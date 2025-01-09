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
  OnDestroy,
  Output,
} from '@angular/core';
import {
  DEFAULT_ROI,
  DeviceFrame,
  LocalDevice,
  ROI,
  SENSOR_SIZE,
} from '../device';
import { CommonModule } from '@angular/common';
import { DialogService } from '@app/layout/dialogs/dialog.service';
import { CardComponent } from '@app/layout/components/card/card.component';
import { LabelsStored } from '@app/layout/pages/data-hub/data-hub.screen';
import { isClassificationInference, Mode } from '../../inference/inference';
import { DevicePipesModule } from '../device.pipes';
import {
  DrawingSurfaceComponent,
  SurfaceMode,
} from '../../drawing/drawing-surface.component';
import { Box, BoxLike, RawDrawing, Point2D } from '@app/core/drawing/drawing';
import { toDrawing } from '../adapters';
import { InferenceResultsService } from '@app/core/inference/inferenceresults.service';
import { ReplaySubject } from 'rxjs';

export const MAX_ERRORS_TERMINATION = 4;
export const TIME_BETWEEN_FRAMES = 2000;

interface StreamOps {
  detach: () => Promise<void>;
}

@Component({
  selector: 'app-device-visualizer',
  standalone: true,
  imports: [
    CommonModule,
    CardComponent,
    DevicePipesModule,
    DrawingSurfaceComponent,
  ],
  templateUrl: './device-visualizer.component.html',
  styleUrl: './device-visualizer.component.scss',
})
export class DeviceVisualizerComponent implements OnDestroy {
  private currentStreamOps?: StreamOps;
  private __roiSetSubject = new ReplaySubject<ROI>(1);
  private __streaming = false;
  private __device?: LocalDevice;
  effectiveRoi = <ROI>{
    offset: new Point2D(0, 0),
    size: SENSOR_SIZE.clone(),
  };
  roi = <ROI>{
    offset: new Point2D(0, 0),
    size: SENSOR_SIZE.clone(),
  };
  errors = 0;
  currentDrawing?: RawDrawing;

  @Input() set device(newDevice: LocalDevice | undefined) {
    this.setDevice(newDevice);
  }

  get device() {
    return this.__device;
  }

  @Input() surfaceMode: SurfaceMode = 'render';
  @Input() mode: Mode = Mode.ImageOnly;
  @Input() labels: LabelsStored = { labels: [], applied: false };
  @Output() frameReceived = new EventEmitter<DeviceFrame>();
  @Output() roiSet$ = this.__roiSetSubject.asObservable();
  @Output() status = new EventEmitter();

  set streaming(s: boolean) {
    this.__streaming = s;
    this.status.emit(s);
  }

  get streaming() {
    return this.__streaming;
  }

  constructor(
    private inferences: InferenceResultsService,
    private prompts: DialogService,
  ) {
    this.__roiSetSubject.next(this.effectiveRoi);
  }

  async setDevice(newDevice: LocalDevice | undefined) {
    const prevDevice = this.__device;
    this.__device = newDevice;
    if (prevDevice?.device_id !== newDevice?.device_id) {
      console.log('New device detected, stopping preview....');
      await this.stopPreview();
      if (newDevice) {
        this.setROI(newDevice.last_known_roi || DEFAULT_ROI);
        if (this.inferences.isDeviceStreaming(newDevice.device_id)) {
          console.log('Device stream cached, restarting!');
          await this.startPreview();
        }
      }
    }
  }

  ngOnDestroy() {
    this.stopPreview();
  }

  public async startPreview() {
    if (!this.streaming && this.device) {
      this.errors = 0;
      this.streaming = true;
      try {
        const { stream, detach } = await this.inferences.getInferencesAsFrame(
          this.device.device_id,
          this.effectiveRoi.offset,
          this.effectiveRoi.size,
          TIME_BETWEEN_FRAMES,
          this.mode,
        );
        const sub = stream.subscribe((frame) => this.handleFrame(frame));
        this.currentStreamOps = {
          detach: async () => {
            sub.unsubscribe();
            await detach();
          },
        };
        // If stop was called while bootstrapping
        if (!this.streaming) this.stopInferenceStream();
        return true;
      } catch (e) {
        console.error('Failed to start stream: ', e);
      }
    }
    await this.stopInferenceStream();
    // generic error
    if (this.mode === Mode.ImageOnly) {
      this.prompts.alert(
        'Failed to stream',
        `Failed to start or get images.`,
        'error',
      );
    } else {
      this.prompts.alert(
        'Failed to stream',
        `Failed to start or get images and inferences.
        Please check that a model and application are loaded on the device,
        and that the configuration parameters sent are compatible.`,
        'error',
      );
    }
    return false;
  }

  public async stopPreview() {
    await this.currentStreamOps?.detach();
    delete this.currentStreamOps;
    delete this.currentDrawing;
    this.streaming = false;
  }

  public async stopInferenceStream(forced = false) {
    await this.stopPreview();
    if (this.device)
      try {
        await this.inferences.stopInferences(this.device.device_id);
      } catch (e) {
        console.error(
          `Couldn't switch device inferences off. Is the device online? [${this.device.device_id}]`,
          e,
        );
      }
    if (forced) {
      this.prompts.alert(
        'Preview stopped',
        `The device failed to produce an image too many times (${MAX_ERRORS_TERMINATION})`,
        'error',
      );
    }
  }

  public async restartPreview() {
    await this.stopInferenceStream();
    await this.startPreview();
  }

  private async handleFrame(frame: DeviceFrame | Error) {
    if (frame instanceof Error) {
      delete this.currentDrawing;
      if (++this.errors >= MAX_ERRORS_TERMINATION)
        await this.stopInferenceStream(true);
    } else {
      if (frame.inference) {
        if (isClassificationInference(frame.inference)) {
          frame.inference.perception.classification_list.forEach((item) => {
            if (item.class_id > this.labels.labels.length - 1) {
              item.label = 'Class ' + item.class_id;
            } else {
              item.label = this.labels.labels[item.class_id];
            }
          });
        } else {
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
}
