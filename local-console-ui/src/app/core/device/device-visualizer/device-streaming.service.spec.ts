/**
 * Copyright 2025 Sony Semiconductor Solutions Corp.
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

import { TestBed } from '@angular/core/testing';
import { Point2D } from '@app/core/drawing/drawing';
import { ExtendedMode, Mode } from '@app/core/inference/inference';
import {
  InferenceResultsService,
  UnknownInferenceFormatError,
} from '@app/core/inference/inferenceresults.service';
import { Device } from '@samplers/device';
import { DEFAULT_ROI, SENSOR_SIZE } from '../device';
import { DirectImageStreamService } from '../image/direct-image-stream.service';
import { DeviceStreamProvider } from './device-stream-provider';
import { DeviceStreamingService } from './device-streaming.service';

class MockInferenceResultsService implements DeviceStreamProvider {
  init = jest.fn();
  teardown = jest.fn();
  getNextFrame = jest.fn();
}

class MockDirectImageStreamService implements DeviceStreamProvider {
  init = jest.fn();
  teardown = jest.fn();
  getNextFrame = jest.fn();
}

const ORIGIN = new Point2D(0, 0);

describe('InferenceResultsService', () => {
  let service: DeviceStreamingService;
  let inferenced: MockInferenceResultsService;
  let direct: MockDirectImageStreamService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        DeviceStreamingService,
        {
          provide: InferenceResultsService,
          useClass: MockInferenceResultsService,
        },
        {
          provide: DirectImageStreamService,
          useClass: MockDirectImageStreamService,
        },
      ],
    });
    service = TestBed.inject(DeviceStreamingService);
    inferenced = TestBed.inject(
      InferenceResultsService,
    ) as unknown as MockInferenceResultsService;
    direct = TestBed.inject(
      DirectImageStreamService,
    ) as unknown as MockDirectImageStreamService;
  });

  describe('setupStreaming', () => {
    it('should start streaming and reflect in cache', async () => {
      const deviceId = '123';
      const mockFrame = Device.sampleFrame();
      inferenced.getNextFrame
        .mockResolvedValueOnce(mockFrame.inference) // For getInference
        .mockResolvedValueOnce(mockFrame.inference) // For convertToJson
        .mockResolvedValueOnce(mockFrame.image); // For getInferenceImage

      inferenced.init.mockResolvedValue(undefined);

      await service.setupStreaming(
        deviceId,
        ORIGIN,
        SENSOR_SIZE,
        Mode.ImageAndInferenceResult,
        'classification',
      );

      expect(inferenced.init).toHaveBeenCalledWith(
        deviceId,
        new Point2D(0, 0),
        SENSOR_SIZE,
        Mode.ImageAndInferenceResult,
      );

      expect(service.isDeviceStreaming(deviceId)).toBeTruthy();

      await service.stopStreaming(deviceId);
    });
  });

  describe('getDeviceStreamAsFrames', () => {
    const DEVICE_ID = 'device-123';

    beforeEach(() => {
      service.setupStreaming(
        DEVICE_ID,
        DEFAULT_ROI.offset,
        DEFAULT_ROI.size,
        Mode.InferenceResult,
        'classification',
      );
    });

    afterEach(() => {
      service.stopStreaming(DEVICE_ID);
    });

    it('emits frames at interval', (done) => {
      const frame = { data: 'frame1' } as any;
      inferenced.getNextFrame.mockResolvedValue(frame);

      service.getDeviceStreamAsFrames(DEVICE_ID).then((stream) => {
        const emitted: any[] = [];

        const sub = stream.subscribe({
          next: (f) => {
            emitted.push(f);
            if (emitted.length === 2) {
              sub.unsubscribe();
              done();
            }
          },
        });
      });
    });

    it('throws if device not streaming', async () => {
      await expect(service.getDeviceStreamAsFrames('unknown')).rejects.toThrow(
        'The device is not streaming',
      );
    });

    it('catches UnknownInferenceFormatError', (done) => {
      const err = new UnknownInferenceFormatError();
      inferenced.getNextFrame.mockResolvedValue(err);

      service.getDeviceStreamAsFrames(DEVICE_ID).then((stream) => {
        stream.subscribe((e) => {
          expect(e).toBe(err);
          done();
        });
      });
    });

    it('wraps unknown errors', (done) => {
      const err = new Error('Cannot get device frame');
      inferenced.getNextFrame.mockResolvedValue(err);

      service.getDeviceStreamAsFrames(DEVICE_ID).then((stream) => {
        stream.subscribe((e) => {
          expect(e).toBe(err);
          done();
        });
      });
    });
  });

  describe('isDeviceStreaming', () => {
    it('should return true only if streaming', async () => {
      const deviceIdA = '123';
      const deviceIdB = '456';

      inferenced.init.mockResolvedValue(undefined);

      await service.setupStreaming(
        deviceIdA,
        ORIGIN,
        SENSOR_SIZE,
        Mode.ImageAndInferenceResult,
        'classification',
      );

      expect(service.isDeviceStreaming(deviceIdA)).toBeTruthy();
      expect(service.isDeviceStreaming(deviceIdB)).toBeFalsy();

      await service.setupStreaming(
        deviceIdB,
        ORIGIN,
        SENSOR_SIZE,
        Mode.ImageAndInferenceResult,
        'classification',
      );

      expect(service.isDeviceStreaming(deviceIdB)).toBeTruthy();

      await service.stopStreaming(deviceIdA);
      await service.stopStreaming(deviceIdB);
    });

    describe('DeviceStreamingService - provider dispatching', () => {
      const deviceId = 'provider-test-device';
      const dummyPoint = new Point2D(1, 1);

      const testProviderCall = async (
        mode: Mode | ExtendedMode,
        expectedProvider: DeviceStreamProvider,
      ) => {
        inferenced.init.mockClear();
        direct.init.mockClear();

        await service.setupStreaming(
          deviceId,
          dummyPoint,
          dummyPoint,
          mode,
          'classification',
        );

        expect(expectedProvider.init).toHaveBeenCalledWith(
          deviceId,
          dummyPoint,
          dummyPoint,
          mode,
        );
        const otherProvider =
          expectedProvider === inferenced ? direct : inferenced;
        expect(otherProvider.init).not.toHaveBeenCalled();
      };

      it('uses InferenceResultsService for Mode.InferenceResult', async () => {
        await testProviderCall(Mode.InferenceResult, inferenced);
      });

      it('uses InferenceResultsService for Mode.ImageAndInferenceResult', async () => {
        await testProviderCall(Mode.ImageAndInferenceResult, inferenced);
      });

      it('uses DirectImageStreamService for Mode.ImageOnly', async () => {
        await testProviderCall(Mode.ImageOnly, direct);
      });

      it('uses DirectImageStreamService for ExtendedMode.Preview', async () => {
        await testProviderCall(ExtendedMode.Preview, direct);
      });
    });
  });
});
