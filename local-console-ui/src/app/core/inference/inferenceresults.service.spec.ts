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

import { TestBed } from '@angular/core/testing';
import { HttpApiClient } from '../common/http/http';
import { DeviceService } from '../device/device.service';
import { InferenceResultsService } from './inferenceresults.service';
import { Device } from '@samplers/device';
import { Point2D } from '../drawing/drawing';
import { SENSOR_SIZE } from '../device/device';
import { Mode } from './inference';

class HttpApiClientMock {
  get = jest.fn();
  getBlob = jest.fn();
}

class DeviceServiceMock {
  startUploadInferenceData = jest.fn();
  stopUploadInferenceData = jest.fn();
}

const ORIGIN = new Point2D(0, 0);
const TIME_BETWEEN_FRAMES = 1000;

describe('InferenceResultsService', () => {
  let service: InferenceResultsService;
  let httpMock: HttpApiClientMock;
  let deviceServiceMock: DeviceServiceMock;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        InferenceResultsService,
        { provide: HttpApiClient, useClass: HttpApiClientMock },
        { provide: DeviceService, useClass: DeviceServiceMock },
      ],
    });
    service = TestBed.inject(InferenceResultsService);
    httpMock = TestBed.inject(HttpApiClient) as unknown as HttpApiClientMock;
    deviceServiceMock = TestBed.inject(
      DeviceService,
    ) as unknown as DeviceServiceMock;
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('getInference', () => {
    it('should retrieve inference data for a device', async () => {
      const deviceId = '123';
      const mockResponse = { data: 'some data' };
      httpMock.get.mockResolvedValue(mockResponse);
      const response = await service.getInference(deviceId);
      expect(httpMock.get).toHaveBeenCalledWith(
        `${service['inferencePath']}/${deviceId}?limit=1`,
        undefined,
        false,
      );
      expect(response).toEqual(mockResponse);
    });

    it('should handle errors when retrieving inference data', async () => {
      const deviceId = '123';
      const error = new Error('Network error');
      httpMock.get.mockRejectedValue(error);
      await expect(service.getInference(deviceId)).rejects.toThrow(
        'Network error',
      );
    });
  });

  describe('getInferencesAsFrame', () => {
    it('should manage an inference frame stream with image and data parsing', async () => {
      const deviceId = '123';
      const mockFrame = Device.sampleFrame();
      httpMock.get
        .mockResolvedValueOnce(mockFrame.inference) // For getInference
        .mockResolvedValueOnce(mockFrame.inference) // For convertToJson
        .mockResolvedValueOnce(mockFrame.image); // For getInferenceImage

      jest.useFakeTimers();
      deviceServiceMock.startUploadInferenceData.mockResolvedValue(undefined);

      const { stream, detach } = await service.getInferencesAsFrame(
        deviceId,
        ORIGIN,
        SENSOR_SIZE,
        TIME_BETWEEN_FRAMES,
        Mode.ImageAndInferenceResult,
      );

      stream.subscribe({
        next: (result) => {
          expect(result).toEqual(mockFrame);
          detach();
        },
      });

      expect(deviceServiceMock.startUploadInferenceData).toHaveBeenCalledWith(
        deviceId,
        new Point2D(0, 0),
        SENSOR_SIZE,
        Mode.ImageAndInferenceResult,
      );

      jest.runOnlyPendingTimers(); // Simulates the timeout for the next tick
      jest.useRealTimers();
    });

    it('should not bootstrap loop when startUploadInferenceData fails', async () => {
      const deviceId = '123';
      const roiOffset = new Point2D(10, 10);
      const roiSize = SENSOR_SIZE;
      const error = new Error('Error starting upload');
      deviceServiceMock.startUploadInferenceData.mockRejectedValue(error);

      try {
        await service.getInferencesAsFrame(
          deviceId,
          roiOffset,
          roiSize,
          TIME_BETWEEN_FRAMES,
          Mode.ImageAndInferenceResult,
        );
        fail();
      } catch (caughtError) {
        expect(caughtError).toBe(error);
      }

      expect(httpMock.get).not.toHaveBeenCalled();
    });
  });

  describe('isDeviceStreaming', () => {
    it('should return true only if streaming', async () => {
      const deviceIdA = '123';
      const deviceIdB = '456';

      deviceServiceMock.startUploadInferenceData.mockResolvedValue(undefined);

      await service.getInferencesAsFrame(
        deviceIdA,
        ORIGIN,
        SENSOR_SIZE,
        TIME_BETWEEN_FRAMES,
        Mode.ImageAndInferenceResult,
      );

      expect(service.isDeviceStreaming(deviceIdA)).toBeTruthy();
      expect(service.isDeviceStreaming(deviceIdB)).toBeFalsy();

      await service.getInferencesAsFrame(
        deviceIdB,
        ORIGIN,
        SENSOR_SIZE,
        TIME_BETWEEN_FRAMES,
        Mode.ImageAndInferenceResult,
      );

      expect(service.isDeviceStreaming(deviceIdB)).toBeTruthy();
    });

    it('should return true even after detached', async () => {
      const deviceIdA = '123';
      const deviceIdB = '456';

      deviceServiceMock.startUploadInferenceData.mockResolvedValue(undefined);

      const aOps = await service.getInferencesAsFrame(
        deviceIdA,
        ORIGIN,
        SENSOR_SIZE,
        TIME_BETWEEN_FRAMES,
        Mode.ImageAndInferenceResult,
      );
      const bOps = await service.getInferencesAsFrame(
        deviceIdB,
        ORIGIN,
        SENSOR_SIZE,
        TIME_BETWEEN_FRAMES,
        Mode.ImageAndInferenceResult,
      );

      bOps.detach();
      expect(service.isDeviceStreaming(deviceIdA)).toBeTruthy();
      expect(service.isDeviceStreaming(deviceIdB)).toBeTruthy();

      aOps.detach();
      expect(service.isDeviceStreaming(deviceIdA)).toBeTruthy();

      await service.stopInferences(deviceIdA);
      expect(service.isDeviceStreaming(deviceIdA)).toBeFalsy();
      expect(service.isDeviceStreaming(deviceIdB)).toBeTruthy();

      await service.stopInferences(deviceIdB);
      expect(service.isDeviceStreaming(deviceIdB)).toBeFalsy();
    });
  });
});
