/**
 * Copyright 2024 Sony Semiconductor Solutions Corp.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  Component,
  EventEmitter,
  Input,
  model,
  OnDestroy,
  Output,
} from '@angular/core';
import { Box, BoxLike, Point2D, RawDrawing } from '@app/core/drawing/drawing';
import { UnknownInferenceFormatError } from '@app/core/inference/inferenceresults.service';
import { DialogService } from '@app/layout/dialogs/dialog.service';
import { LabelsStored } from '@app/layout/pages/data-hub/data-hub.screen';
import { ReplaySubject } from 'rxjs';
import {
  DrawingState,
  DrawingSurfaceComponent,
  SurfaceMode,
} from '../../drawing/drawing-surface.component';
import {
  ExtendedMode,
  isClassificationInference,
  isDetectionInference,
  Mode,
} from '../../inference/inference';
import { toDrawing } from '../adapters';
import { OperationMode } from '../configuration';
import {
  DEFAULT_ROI,
  DeviceFrame,
  LocalDevice,
  ROI,
  SENSOR_SIZE,
} from '../device';
import { DevicePipesModule } from '../device.pipes';
import { DeviceStreamingService } from './device-streaming.service';

export const MAX_INACTIVITY_BEFORE_DRAWING_CLEAR_MS = 5 * 1000;
export const MAX_INACTIVITY_BEFORE_INFERENCE_STOP_MS = 30 * 1000;

interface StreamOps {
  detach: () => Promise<void>;
}

@Component({
  selector: 'app-device-visualizer',
  standalone: true,
  imports: [DevicePipesModule, DrawingSurfaceComponent],
  templateUrl: './device-visualizer.component.html',
  styleUrl: './device-visualizer.component.scss',
})
export class DeviceVisualizerComponent implements OnDestroy {
  private currentStreamOps?: StreamOps;
  private __roiSetSubject = new ReplaySubject<ROI>(1);
  private __device?: LocalDevice;
  effectiveRoi = <ROI>{
    offset: new Point2D(0, 0),
    size: SENSOR_SIZE.clone(),
  };
  roi = <ROI>{
    offset: new Point2D(0, 0),
    size: SENSOR_SIZE.clone(),
  };
  latestValidFrameTimestamp: undefined | number;
  currentDrawing?: RawDrawing;

  @Input() set device(newDevice: LocalDevice | undefined) {
    this.setDevice(newDevice);
  }

  get device() {
    return this.__device;
  }

  @Input() surfaceMode: SurfaceMode = 'render';
  @Input() mode: Mode | ExtendedMode = Mode.ImageOnly;
  @Input() type: OperationMode = 'custom';
  @Input() labels: LabelsStored = { labels: [], applied: false };
  @Output() frameReceived = new EventEmitter<DeviceFrame>();
  @Output() roiSet$ = this.__roiSetSubject.asObservable();

  drawingState = model(DrawingState.Disabled);

  constructor(
    private streams: DeviceStreamingService,
    private prompts: DialogService,
  ) {
    this.__roiSetSubject.next(this.effectiveRoi);
  }

  streaming() {
    return this.drawingState() === DrawingState.Streaming;
  }

  error() {
    return this.drawingState() === DrawingState.Error;
  }

  async setDevice(newDevice: LocalDevice | undefined) {
    const prevDevice = this.__device;
    this.__device = newDevice;
    if (prevDevice?.device_id !== newDevice?.device_id) {
      console.log('New device detected, stopping preview....');
      await this.stopPreview();
      if (newDevice) {
        this.setROI(newDevice.last_known_roi || DEFAULT_ROI);
        if (this.streams.isDeviceStreaming(newDevice.device_id)) {
          console.log('Device stream cached, restarting!');
          await this.hookStream();
        }
      }
    }
  }

  ngOnDestroy() {
    this.stopPreview();
  }

  public async startPreview() {
    if (!this.streaming() && this.device) {
      try {
        this.drawingState.set(DrawingState.Streaming);
        await this.streams.setupStreaming(
          this.device.device_id,
          this.effectiveRoi.offset,
          this.effectiveRoi.size,
          this.mode,
          this.type,
        );
        await this.hookStream();
        // If stop was called while bootstrapping
        if (!this.streaming()) await this.stopInferenceStream();
        return true;
      } catch (e) {
        console.error('Failed to start stream: ', e);
      }
    }
    // generic error
    this.prompts.alert(
      'Failed to stream',
      `Failed to start or get images and inferences.
      Please check that a model and application are loaded on the device,
      and that the configuration parameters sent are compatible.`,
      'error',
    );
    await this.stopInferenceStream();
    return false;
  }

  private async hookStream() {
    this.drawingState.set(DrawingState.Streaming);
    const stream = await this.streams.getDeviceStreamAsFrames(
      this.device!.device_id,
    );
    const sub = stream.subscribe((frame) => this.handleFrame(frame));
    this.currentStreamOps = {
      detach: async () => {
        sub.unsubscribe();
      },
    };
  }

  public async stopPreview() {
    this.drawingState.set(DrawingState.Disabled);
    await this.currentStreamOps?.detach();
    delete this.currentStreamOps;
    delete this.currentDrawing;
  }

  public async stopInferenceStream(forced = false) {
    await this.stopPreview();
    if (forced) {
      this.prompts.alert(
        'Preview stopped',
        `The device failed to produce an image after ${MAX_INACTIVITY_BEFORE_INFERENCE_STOP_MS} milliseconds`,
        'error',
      );
    }
    if (this.device)
      try {
        await this.streams.stopStreaming(this.device.device_id);
      } catch (e) {
        console.error(
          `Couldn't switch device inferences off. Is the device online? [${this.device.device_id}]`,
          e,
        );
      }
  }

  public async restartPreview() {
    await this.stopInferenceStream();
    await this.startPreview();
  }

  private async handleFrame(frame: DeviceFrame | Error) {
    if (!this.streaming()) return;
    if (!this.latestValidFrameTimestamp) {
      // Initialize in first `handleFrame` in case there's no valid frame at any time
      this.latestValidFrameTimestamp = this.getNow();
    }

    if (frame instanceof UnknownInferenceFormatError) {
      await this.stopInferenceStream();
      this.drawingState.set(DrawingState.Error);
    } else if (frame instanceof Error) {
      const timeSinceLastValidFrame =
        this.getNow() - this.latestValidFrameTimestamp;
      if (timeSinceLastValidFrame > MAX_INACTIVITY_BEFORE_DRAWING_CLEAR_MS)
        delete this.currentDrawing;
      if (timeSinceLastValidFrame > MAX_INACTIVITY_BEFORE_INFERENCE_STOP_MS)
        await this.stopInferenceStream(true);
    } else {
      // if valid new frame, reset timestamp
      this.latestValidFrameTimestamp = this.getNow();
      if (frame.inference) {
        if (isClassificationInference(frame.inference)) {
          frame.inference.perception.classification_list.forEach((item) => {
            if (item.class_id > this.labels.labels.length - 1) {
              item.label = 'Class ' + item.class_id;
            } else {
              item.label = this.labels.labels[item.class_id];
            }
          });
        } else if (isDetectionInference(frame.inference)) {
          frame.inference.perception.object_detection_list.forEach((item) => {
            if (item.class_id > this.labels.labels.length - 1) {
              item.label = 'Class ' + item.class_id;
            } else {
              item.label = this.labels.labels[item.class_id];
            }
          });
        }
      }

      this.currentDrawing = toDrawing(frame);

      this.frameReceived.emit(frame);
    }
  }

  onROISelected(roi: BoxLike) {
    const expandedROI = new Box(roi).vectMul(SENSOR_SIZE);
    this.roi = {
      offset: expandedROI.min.round(),
      size: expandedROI.size().round(),
    };
  }

  async makeROIEffective() {
    this.setROI(this.cloneROI(this.roi));
    await this.restartPreview();
  }

  async resetROI() {
    this.setROI(this.cloneROI(DEFAULT_ROI));
    await this.restartPreview();
  }

  private setROI(newROI: ROI) {
    this.effectiveRoi = this.cloneROI(newROI);
    this.roi = this.cloneROI(newROI);
    this.surfaceMode = 'render';
    this.__roiSetSubject.next(this.effectiveRoi);
  }

  // TODO: move this?
  private cloneROI(roi: ROI): ROI {
    return {
      offset: roi.offset.clone(),
      size: roi.size.clone(),
    };
  }

  private getNow(): number {
    return Date.now();
  }
}
