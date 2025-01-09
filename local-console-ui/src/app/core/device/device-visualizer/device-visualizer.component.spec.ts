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
  ComponentFixture,
  fakeAsync,
  TestBed,
  tick,
} from '@angular/core/testing';

import {
  DeviceVisualizerComponent,
  MAX_ERRORS_TERMINATION,
} from './device-visualizer.component';
import { Device } from '@samplers/device';
import { DialogService } from '@app/layout/dialogs/dialog.service';
import { Subject } from 'rxjs';
import { Component, Input } from '@angular/core';
import { InferenceResultsService } from '@app/core/inference/inferenceresults.service';
import { Box, BoxLike, Drawing, Point2D } from '@app/core/drawing/drawing';
import { DrawingSurfaceComponent } from '@app/core/drawing/drawing-surface.component';
import { Mode } from '@app/core/inference/inference';
import { waitForExpect } from '@test/utils';
import { ROI, SENSOR_SIZE } from '../device';

class MockInferencesService {
  getInferences = jest.fn();
  getInferencesAsFrame = jest.fn();
  stopInferences = jest.fn();
  isDeviceStreaming = jest.fn();
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
  let inferencesService: MockInferencesService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DeviceVisualizerComponent, MockDrawingSurfaceComponent],
      providers: [
        { provide: DialogService, useClass: MockDialogService },
        { provide: InferenceResultsService, useClass: MockInferencesService },
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
    inferencesService = TestBed.inject(
      InferenceResultsService,
    ) as unknown as MockInferencesService;
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
      const device = Device.sampleLocal();

      const mock = inferencesService.getInferencesAsFrame.mockReturnValue({
        stream: new Subject(),
        detach: jest.fn(),
      });
      await component.setDevice(device);

      await component.startPreview();

      expect(component.streaming).toBeTruthy();
      expect(mock).toHaveBeenCalledWith(
        device.device_id,
        expect.any(Point2D),
        expect.any(Point2D),
        expect.any(Number),
        Mode.ImageOnly,
      );
    });

    it('should handle errors during streaming and stop after max errors', async () => {
      const device = Device.sampleLocal();
      const stream = new Subject();
      const detach = jest.fn();

      inferencesService.getInferencesAsFrame.mockReturnValue({
        stream,
        detach,
      });
      await component.setDevice(device);

      await component.startPreview();
      expect(component.streaming).toBeTruthy();

      const errorsToTest = MAX_ERRORS_TERMINATION + 1; // simulate one extra to test boundary
      for (let i = 0; i < errorsToTest; i++) {
        stream.next(new Error('Stream error'));
      }

      await waitForExpect(() => {
        expect(component.errors).toBe(MAX_ERRORS_TERMINATION);
        expect(component.streaming).toBeFalsy();
        expect(detach).toHaveBeenCalled();
        expect(dialogService.alert).toHaveBeenCalledWith(
          'Preview stopped',
          `The device failed to produce an image too many times (${MAX_ERRORS_TERMINATION})`,
          'error',
        );
      });
    });

    it('should unsubscribe and stop streaming when component is destroyed', async () => {
      const device = Device.sampleLocal();
      const detach = jest.fn();
      inferencesService.getInferencesAsFrame.mockReturnValue({
        stream: new Subject(),
        detach: detach,
      });
      await component.setDevice(device);

      await component.startPreview();

      component.ngOnDestroy();
      await waitForExpect(() => {
        expect(component.streaming).toBeFalsy();
        expect(detach).toHaveBeenCalled();
      });
    });

    it('should reset everything even if component reports as not streaming', async () => {
      const device = Device.sampleLocal();
      const detach = jest.fn();

      inferencesService.getInferencesAsFrame.mockReturnValue({
        stream: new Subject(),
        detach: detach,
      });
      await component.setDevice(device);

      await component.startPreview();
      component.streaming = false;

      component.stopPreview();

      expect(detach).toHaveBeenCalled();
    });

    it('should start preview in Mode.ImageOnly', async () => {
      const device = Device.sampleLocal();
      component.mode = Mode.ImageOnly;

      await component.setDevice(device);

      const mock = inferencesService.getInferencesAsFrame.mockReturnValue({
        stream: new Subject(),
        detach: jest.fn(),
      });

      await component.startPreview();

      expect(component.streaming).toBeTruthy();
      expect(mock).toHaveBeenCalledWith(
        device.device_id,
        expect.any(Point2D),
        expect.any(Point2D),
        expect.any(Number),
        Mode.ImageOnly,
      );
    });

    it('should start preview in Mode.ImageAndInferenceResult', async () => {
      const device = Device.sampleLocal();
      component.mode = Mode.ImageAndInferenceResult;

      await component.setDevice(device);
      const mock = inferencesService.getInferencesAsFrame.mockReturnValue({
        stream: new Subject(),
        detach: jest.fn(),
      });

      await component.startPreview();

      expect(component.streaming).toBeTruthy();
      expect(mock).toHaveBeenCalledWith(
        device.device_id,
        expect.any(Point2D),
        expect.any(Point2D),
        expect.any(Number),
        Mode.ImageAndInferenceResult,
      );
    });

    it('should toggle mode and restart preview correctly', async () => {
      const device = Device.sampleLocal();

      await component.setDevice(device);

      const mock = inferencesService.getInferencesAsFrame.mockReturnValue({
        stream: new Subject(),
        detach: jest.fn().mockResolvedValue(undefined),
      });

      // Start in ImageOnly mode
      component.mode = Mode.ImageOnly;
      await component.startPreview();

      expect(component.streaming).toBeTruthy();
      expect(mock).toHaveBeenCalledWith(
        device.device_id,
        expect.any(Point2D),
        expect.any(Point2D),
        expect.any(Number),
        Mode.ImageOnly,
      );

      // Change to ImageAndInferenceResult mode and restart
      await component.stopInferenceStream();
      component.mode = Mode.ImageAndInferenceResult;
      await component.startPreview();

      expect(component.streaming).toBeTruthy();
      expect(mock).toHaveBeenCalledWith(
        device.device_id,
        expect.any(Point2D),
        expect.any(Point2D),
        expect.any(Number),
        Mode.ImageAndInferenceResult,
      );
    });

    it('should gracefully shutdown preview and alert user if streaming cannot be started', async () => {
      const device = Device.sampleLocal();

      inferencesService.getInferencesAsFrame.mockRejectedValue(new Error());
      await component.setDevice(device);

      const state = await component.startPreview();

      expect(state).toBeFalsy();

      expect(inferencesService.stopInferences).toHaveBeenCalled();
      expect(dialogService.alert).toHaveBeenCalledWith(
        'Failed to stream',
        expect.any(String),
        'error',
      );
    });

    it('should automatically start previewing device if cache is hit', async () => {
      const device = Device.sampleLocal();
      const newDevice = Device.sampleLocal(
        Device.sample('second device', 'second_device'),
        6543,
      );
      const stream = new Subject();
      const detach = jest.fn().mockResolvedValue(undefined);
      await component.setDevice(device);
      inferencesService.getInferencesAsFrame.mockResolvedValue({
        stream,
        detach,
      });
      console.log('start...');
      await component.startPreview();
      console.log('started, streaming is: ' + component.streaming);

      expect(component.streaming).toBeTruthy();
      expect(inferencesService.getInferencesAsFrame).toHaveBeenCalledWith(
        device.device_id,
        expect.any(Point2D),
        expect.any(Point2D),
        expect.any(Number),
        component.mode,
      );

      inferencesService.isDeviceStreaming.mockReturnValue(true);

      await component.setDevice(newDevice);
      expect(component.streaming).toBeTruthy();

      await waitForExpect(() => {
        expect(detach).toHaveBeenCalled();
        expect(inferencesService.isDeviceStreaming).toHaveBeenCalledWith(
          newDevice.device_id,
        );
        expect(inferencesService.getInferencesAsFrame).toHaveBeenCalledWith(
          newDevice.device_id,
          expect.any(Point2D),
          expect.any(Point2D),
          expect.any(Number),
          component.mode,
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
        const device = Device.sampleLocal();
        await component.setDevice(device);
        component.roi = {
          offset: new Point2D(10, 10),
          size: new Point2D(20, 20),
        };
        let emittedROI: ROI | undefined;
        const detach = jest.fn();
        inferencesService.getInferencesAsFrame.mockReturnValue({
          stream: new Subject(),
          detach: detach,
        });
        component.roiSet$.subscribe((roi) => (emittedROI = roi)); // Subscribe to observe emitted ROI

        await component.makeROIEffective();

        expect(inferencesService.stopInferences).toHaveBeenCalled();
        expect(inferencesService.getInferencesAsFrame).toHaveBeenCalledWith(
          device.device_id,
          new Point2D(10, 10),
          new Point2D(20, 20),
          expect.any(Number),
          component.mode,
        );
      });
    });

    describe('resetROI', () => {
      it('should reset ROI and effective ROI, stop inference stream, emit ROI, and start preview', async () => {
        const device = Device.sampleLocal();
        await component.setDevice(device);
        let emittedROI: ROI | undefined;
        component.roiSet$.subscribe((roi) => (emittedROI = roi)); // Subscribe to observe emitted ROI

        await component.resetROI();

        // Assert
        expect(component.effectiveRoi.offset).toEqual(new Point2D(0, 0));
        expect(component.effectiveRoi.size).toEqual(SENSOR_SIZE.clone());
        expect(component.roi.offset).toEqual(new Point2D(0, 0));
        expect(component.roi.size).toEqual(SENSOR_SIZE.clone());
        expect(inferencesService.stopInferences).toHaveBeenCalled();
        expect(inferencesService.getInferencesAsFrame).toHaveBeenCalledWith(
          device.device_id,
          new Point2D(0, 0),
          SENSOR_SIZE,
          expect.any(Number),
          component.mode,
        );
        expect(emittedROI).toEqual(component.effectiveRoi);
      });
    });
  });
});
