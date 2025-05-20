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

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Component, Input } from '@angular/core';
import { Box, BoxLike, Drawing, Point2D } from '@app/core/drawing/drawing';
import {
  DrawingState,
  DrawingSurfaceComponent,
} from '@app/core/drawing/drawing-surface.component';
import { Mode } from '@app/core/inference/inference';
import { DialogService } from '@app/layout/dialogs/dialog.service';
import { Device } from '@samplers/device';
import { waitForExpect } from '@test/utils';
import { Subject } from 'rxjs';
import { DeviceFrame, ROI, SENSOR_SIZE } from '../device';
import { DeviceStreamingService } from './device-streaming.service';
import {
  DeviceVisualizerComponent,
  MAX_INACTIVITY_BEFORE_DRAWING_CLEAR_MS,
  MAX_INACTIVITY_BEFORE_INFERENCE_STOP_MS,
} from './device-visualizer.component';

class MockDeviceStreamingService implements Required<DeviceStreamingService> {
  getDeviceStreamAsFrames = jest.fn();
  stopStreaming = jest.fn();
  isDeviceStreaming = jest.fn();
  setupStreaming = jest.fn();
  getStreamingMode = jest.fn();
}
class MockDialogService {
  alert = jest.fn();
}
@Component({
  selector: 'app-drawing',
  standalone: true,
  template: `<div></div>`,
})
export class MockDrawingSurfaceComponent {
  @Input() drawing?: Drawing;
  @Input() enabled = false;
  @Input() mode = Mode.ImageOnly;
}

describe('StreamingPreviewComponent', () => {
  let component: DeviceVisualizerComponent;
  let fixture: ComponentFixture<DeviceVisualizerComponent>;
  let dialogService: MockDialogService;
  let streamingService: jest.Mocked<Required<DeviceStreamingService>>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DeviceVisualizerComponent, MockDrawingSurfaceComponent],
      providers: [
        { provide: DialogService, useClass: MockDialogService },
        {
          provide: DeviceStreamingService,
          useClass: MockDeviceStreamingService,
        },
      ],
    })
      .overrideComponent(DeviceVisualizerComponent, {
        remove: { imports: [DrawingSurfaceComponent] },
        add: {
          imports: [MockDrawingSurfaceComponent],
        },
      })
      .compileComponents();

    fixture = TestBed.createComponent(DeviceVisualizerComponent);
    streamingService = TestBed.inject(
      DeviceStreamingService,
    ) as unknown as MockDeviceStreamingService;
    dialogService = TestBed.inject(
      DialogService,
    ) as unknown as MockDialogService;
    component = fixture.componentInstance;

    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('previewing', () => {
    it('should start preview if not already streaming and a device is selected', async () => {
      const device = Device.sample();

      streamingService.getDeviceStreamAsFrames.mockResolvedValue(new Subject());
      await component.setDevice(device);

      await component.startPreview();

      expect(component.streaming()).toBeTruthy();
      expect(streamingService.getDeviceStreamAsFrames).toHaveBeenCalledWith(
        device.device_id,
      );
    });

    it('should handle errors during streaming and stop after timeout', async () => {
      const device = Device.sample();
      const stream = new Subject<DeviceFrame | Error>();

      streamingService.getDeviceStreamAsFrames.mockResolvedValue(stream);
      await component.setDevice(device);
      await component.startPreview();
      expect(component.streaming()).toBeTruthy();

      const nowSpy = jest.spyOn(component as any, 'getNow');
      nowSpy.mockReturnValueOnce(0);
      nowSpy.mockReturnValueOnce(MAX_INACTIVITY_BEFORE_DRAWING_CLEAR_MS + 1);
      nowSpy.mockReturnValueOnce(MAX_INACTIVITY_BEFORE_INFERENCE_STOP_MS + 1);

      // first error, show "Getting image..."
      stream.next(new Error('Stream error'));

      await waitForExpect(() => {
        expect(component.streaming()).toBeTruthy();
        expect(dialogService.alert).not.toHaveBeenCalledWith();
      });

      // last error, stop inference
      stream.next(new Error('Stream error'));

      await waitForExpect(() => {
        expect(component.streaming()).toBeFalsy();
        expect(dialogService.alert).toHaveBeenCalledWith(
          'Preview stopped',
          `The device failed to produce an image after ${MAX_INACTIVITY_BEFORE_INFERENCE_STOP_MS} milliseconds`,
          'error',
        );
      });
    });

    it('should unsubscribe and stop streaming when component is destroyed', async () => {
      const device = Device.sample();
      streamingService.getDeviceStreamAsFrames.mockResolvedValue(new Subject());
      await component.setDevice(device);

      await component.startPreview();

      component.ngOnDestroy();
      await waitForExpect(() => {
        expect(component.streaming()).toBeFalsy();
      });
    });

    it('should reset everything even if component reports as not streaming', async () => {
      const device = Device.sample();

      streamingService.getDeviceStreamAsFrames.mockResolvedValue(new Subject());
      await component.setDevice(device);

      await component.startPreview();
      component.drawingState.set(DrawingState.Disabled);

      component.stopPreview();
    });

    it('should start preview in Mode.ImageOnly', async () => {
      const device = Device.sample();
      component.mode = Mode.ImageOnly;

      await component.setDevice(device);

      streamingService.getDeviceStreamAsFrames.mockResolvedValue(new Subject());

      await component.startPreview();

      expect(component.streaming()).toBeTruthy();
      expect(streamingService.getDeviceStreamAsFrames).toHaveBeenCalledWith(
        device.device_id,
      );
    });

    it('should start preview in Mode.ImageAndInferenceResult', async () => {
      const device = Device.sample();
      component.mode = Mode.ImageAndInferenceResult;

      await component.setDevice(device);
      streamingService.getDeviceStreamAsFrames.mockResolvedValue(new Subject());

      await component.startPreview();

      expect(component.streaming).toBeTruthy();
      expect(streamingService.getDeviceStreamAsFrames).toHaveBeenCalledWith(
        device.device_id,
      );
    });

    it('should toggle mode and restart preview correctly', async () => {
      const device = Device.sample();

      await component.setDevice(device);

      streamingService.getDeviceStreamAsFrames.mockResolvedValue(new Subject());

      // Start in ImageOnly mode
      component.mode = Mode.ImageOnly;
      await component.startPreview();

      expect(component.streaming()).toBeTruthy();
      expect(streamingService.getDeviceStreamAsFrames).toHaveBeenCalledWith(
        device.device_id,
      );

      // Change to ImageAndInferenceResult mode and restart
      await component.stopInferenceStream();
      component.mode = Mode.ImageAndInferenceResult;
      await component.startPreview();

      expect(component.streaming()).toBeTruthy();
      expect(streamingService.getDeviceStreamAsFrames).toHaveBeenCalledWith(
        device.device_id,
      );
    });

    it('should gracefully shutdown preview and alert user if streaming cannot be started', async () => {
      const device = Device.sample();

      streamingService.getDeviceStreamAsFrames.mockRejectedValue(new Error());
      await component.setDevice(device);

      const state = await component.startPreview();

      expect(state).toBeFalsy();

      expect(streamingService.stopStreaming).toHaveBeenCalled();
      expect(dialogService.alert).toHaveBeenCalledWith(
        'Failed to stream',
        expect.any(String),
        'error',
      );
    });

    it('should automatically start previewing device if cache is hit', async () => {
      const device = Device.sample();
      const newDevice = Device.sample({
        device_name: 'second device',
        device_id: '6543',
      });
      const stream = new Subject<DeviceFrame | Error>();
      await component.setDevice(device);
      streamingService.getDeviceStreamAsFrames.mockResolvedValue(new Subject());
      console.log('start...');
      await component.startPreview();
      console.log('started, streaming is: ' + component.streaming());

      expect(component.streaming()).toBeTruthy();
      expect(streamingService.getDeviceStreamAsFrames).toHaveBeenCalledWith(
        device.device_id,
      );

      streamingService.isDeviceStreaming.mockReturnValue(true);

      await component.setDevice(newDevice);
      expect(component.streaming()).toBeTruthy();

      await waitForExpect(() => {
        expect(streamingService.isDeviceStreaming).toHaveBeenCalledWith(
          newDevice.device_id,
        );
        expect(streamingService.getDeviceStreamAsFrames).toHaveBeenCalledWith(
          newDevice.device_id,
        );
      });
    });
  });

  describe('roi', () => {
    describe('onROISelected', () => {
      it('should correctly expand and set the ROI based on the selected box', () => {
        const roi: BoxLike = {
          min: new Point2D(0.2, 0.2),
          max: new Point2D(0.5, 0.5),
        };
        const expectedExpandedROI = new Box({
          min: new Point2D(SENSOR_SIZE.x / 5, SENSOR_SIZE.y / 5),
          max: new Point2D(SENSOR_SIZE.x / 2, SENSOR_SIZE.y / 2),
        });

        component.onROISelected(roi);

        expect(component.roi.offset).toEqual(expectedExpandedROI.min.round());
        expect(component.roi.size).toEqual(expectedExpandedROI.size().round());
      });
    });

    describe('makeROIEffective', () => {
      it('should set effective ROI, stop inference stream, emit ROI, and start preview', async () => {
        const device = Device.sample();
        await component.setDevice(device);
        component.roi = {
          offset: new Point2D(10, 10),
          size: new Point2D(20, 20),
        };
        let emittedROI: ROI | undefined;
        streamingService.getDeviceStreamAsFrames.mockResolvedValue(
          new Subject(),
        );
        component.roiSet$.subscribe((roi) => (emittedROI = roi)); // Subscribe to observe emitted ROI

        await component.makeROIEffective();

        expect(streamingService.stopStreaming).toHaveBeenCalled();
        expect(streamingService.setupStreaming).toHaveBeenCalledWith(
          device.device_id,
          new Point2D(10, 10),
          new Point2D(20, 20),
          component.mode,
          'custom',
        );
        expect(streamingService.getDeviceStreamAsFrames).toHaveBeenCalledWith(
          device.device_id,
        );
      });
    });

    describe('resetROI', () => {
      it('should reset ROI and effective ROI, stop inference stream, emit ROI, and start preview', async () => {
        const device = Device.sample();
        await component.setDevice(device);
        let emittedROI: ROI | undefined;
        component.roiSet$.subscribe((roi) => (emittedROI = roi)); // Subscribe to observe emitted ROI

        await component.resetROI();

        // Assert
        expect(component.effectiveRoi.offset).toEqual(new Point2D(0, 0));
        expect(component.effectiveRoi.size).toEqual(SENSOR_SIZE.clone());
        expect(component.roi.offset).toEqual(new Point2D(0, 0));
        expect(component.roi.size).toEqual(SENSOR_SIZE.clone());
        expect(streamingService.stopStreaming).toHaveBeenCalled();
        expect(streamingService.getDeviceStreamAsFrames).toHaveBeenCalledWith(
          device.device_id,
        );
        expect(emittedROI).toEqual(component.effectiveRoi);
      });
    });
  });
});
