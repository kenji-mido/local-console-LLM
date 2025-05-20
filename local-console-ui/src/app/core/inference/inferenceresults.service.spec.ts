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
import { Inferences } from '@samplers/inferences';
import { HttpApiClient } from '../common/http/http';
import { OperationMode } from '../device/configuration';
import { DeviceFrame } from '../device/device';
import { Point2D } from '../drawing/drawing';
import { ModuleConfigService } from '../module/module-config.service';
import {
  Classification,
  Detection,
  ErrorInference,
  ExtendedMode,
  Mode,
  TaskType,
} from './inference';
import {
  InferenceResultsService,
  TaskTypeOperationsModeMap,
} from './inferenceresults.service';
import {
  isClassificationItem,
  isDetectionItem,
} from './inferenceresults.utils';

class HttpApiClientMock {
  get = jest.fn();
  getblob = jest.fn();
}

class MockedModuleConfigService implements Required<ModuleConfigService> {
  getModuleProperty = jest.fn();
  patchModuleConfiguration = jest.fn();
}

describe('InferenceResultsService', () => {
  let service: InferenceResultsService;
  let httpMock: HttpApiClientMock;
  let moduleConfigService: jest.Mocked<Required<ModuleConfigService>>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        InferenceResultsService,
        { provide: HttpApiClient, useClass: HttpApiClientMock },
        { provide: ModuleConfigService, useClass: MockedModuleConfigService },
      ],
    });
    service = TestBed.inject(InferenceResultsService);
    httpMock = TestBed.inject(HttpApiClient) as unknown as HttpApiClientMock;
    moduleConfigService = TestBed.inject(
      ModuleConfigService,
    ) as unknown as MockedModuleConfigService;
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('getLastInference', () => {
    it('should retrieve inference data for a device', async () => {
      const deviceId = '123';
      const inferenceResult = { Inferences: [{ T: 'NAME1' }] };
      const mockResponse = {
        data: [{ inference_result: inferenceResult }],
        continuation_token: 'TOKEN1',
      };
      httpMock.get.mockResolvedValue(mockResponse);
      const response = await service.getLastInference(deviceId);
      expect(httpMock.get).toHaveBeenCalledWith(
        `${service['inferencePath']}/${deviceId}?limit=1`,
        {},
        false,
      );
      expect(response).toEqual({ inferenceResult, identifier: 'NAME1' });
    });

    it('should handle errors when retrieving inference data', async () => {
      const deviceId = '123';
      const error = new Error('Network error');
      httpMock.get.mockRejectedValue(error);
      await expect(service.getLastInference(deviceId)).rejects.toThrow(
        'Network error',
      );
    });

    it('should return error if continuation_token is the same as latest', async () => {
      const deviceId = '123';
      httpMock.get.mockResolvedValue({
        data: [{ inference_result: 'some data' }],
        continuation_token: 'TOKEN1',
      });
      await expect(
        service.getLastInference(deviceId, 'TOKEN1'),
      ).rejects.toThrow();
    });
  });

  describe('getLatestImageDescriptor', () => {
    it('should retrieve inference data for a device', async () => {
      const deviceId = '123';
      httpMock.get.mockResolvedValue({
        data: [{ name: 'some name', sas_url: 'some sas_url' }],
        continuation_token: 'TOKEN1',
      });
      const response = await service.getLatestImageDescriptor(deviceId);
      expect(httpMock.get).toHaveBeenCalledWith(
        `${service['imagePath']}/${deviceId}/directories?limit=1`,
        {},
        false,
      );
      expect(response).toEqual({
        name: 'some name',
        sasUrl: 'some sas_url',
        identifier: 'some name',
      });
    });

    it('should return error if continuation_token is the same as latest', async () => {
      const deviceId = '123';
      httpMock.get.mockResolvedValue({
        data: [{ name: 'some name', sas_url: 'some sas_url' }],
        continuation_token: 'TOKEN1',
      });
      await expect(
        service.getLatestImageDescriptor(deviceId, 'some name'),
      ).rejects.toThrow();
    });
  });

  describe('checkTaskTypeOperationModeMatch', () => {
    it('should return inference if tasktype undefined or tasktype and operationmode match', async () => {
      let taskType = undefined;
      let operationMode: OperationMode = 'classification';
      let mockInference = Inferences.sample('classification');
      let result = service.checkTaskTypeOperationModeMatch(
        taskType,
        operationMode,
        mockInference,
      );

      expect(result).toEqual(mockInference);

      taskType = TaskType.Classification;
      result = service.checkTaskTypeOperationModeMatch(
        taskType,
        operationMode,
        mockInference,
      );

      operationMode = 'detection';
      taskType = TaskType.ObjectDetection;
      result = service.checkTaskTypeOperationModeMatch(
        taskType,
        operationMode,
        mockInference,
      );

      expect(result).toEqual(mockInference);

      operationMode = 'generic_classification';
      taskType = TaskType.Classification;
      result = service.checkTaskTypeOperationModeMatch(
        taskType,
        operationMode,
        mockInference,
      );

      expect(result).toEqual(mockInference);

      operationMode = 'generic_detection';
      taskType = TaskType.ObjectDetection;
      result = service.checkTaskTypeOperationModeMatch(
        taskType,
        operationMode,
        mockInference,
      );

      expect(result).toEqual(mockInference);
    });

    it('should return error inference if inference is Error or tasktype and operation mode NOT match', async () => {
      let taskType = TaskType.Classification;
      let operationMode: OperationMode = 'classification';
      let mockInference = Inferences.sample('error');
      let result = service.checkTaskTypeOperationModeMatch(
        taskType,
        operationMode,
        mockInference,
      );

      expect(result).toEqual(mockInference);

      taskType = TaskType.ObjectDetection;
      mockInference = Inferences.sample('classification');
      result = service.checkTaskTypeOperationModeMatch(
        taskType,
        operationMode,
        mockInference,
      );

      expect(result).toEqual(<ErrorInference>{
        errorLabel: `The task type reported by the application running in the device is ${TaskTypeOperationsModeMap[taskType][0]},
            but ${service.getOperationTypeName(operationMode)} was expected for the given Operation Mode.`,
      });
    });
  });

  describe('init', () => {
    it('should start inference upload with correct parameters', async () => {
      const deviceId = 'dev1';
      const roiOffset = new Point2D(0, 0);
      const roiSize = new Point2D(100, 100);
      const mode = Mode.ImageAndInferenceResult;

      await service.init(deviceId, roiOffset, roiSize, mode);

      expect(moduleConfigService.patchModuleConfiguration).toHaveBeenCalledWith(
        deviceId,
        expect.any(String),
        expect.objectContaining({
          common_settings: {
            process_state: 2,
            pq_settings: {
              image_cropping: {
                left: 0,
                top: 0,
                width: 100,
                height: 100,
              },
            },
            port_settings: {
              input_tensor: {
                enabled: true,
              },
              metadata: {
                enabled: true,
              },
            },
          },
        }),
      );
    });
  });

  describe('teardown', () => {
    it('should stop inference upload for device', async () => {
      const deviceId = 'dev1';

      await service.teardown(deviceId);

      expect(moduleConfigService.patchModuleConfiguration).toHaveBeenCalledWith(
        deviceId,
        expect.any(String),
        expect.objectContaining({
          common_settings: {
            port_settings: {
              input_tensor: {
                enabled: false,
              },
              metadata: {
                enabled: false,
              },
            },
          },
        }),
      );
    });
  });

  describe('getNextFrame', () => {
    const deviceId = 'dev1';
    const name = 'NAME1';
    const name_inf = name + '.txt';
    const name_img = name + '.jpg';

    let abortController: AbortController;

    beforeEach(() => {
      abortController = new AbortController();
    });

    it('should return device frame if mode base64encoded and inference correct', async () => {
      const inferenceResult = {
        Inferences: [{ T: name, F: 0, O: 'classification_inference' }],
      };
      const mockResponse = {
        data: [
          {
            id: name,
            inference: { id: name_inf, inference_result: inferenceResult },
            image: { name: name_img, sas_url: name_img },
          },
        ],
        continuation_token: 'TOKEN1',
      };
      httpMock.get.mockResolvedValueOnce(mockResponse);

      const mock_inf_classification = Inferences.sample('classification');
      httpMock.get.mockResolvedValueOnce(mock_inf_classification);

      const encoder = new TextEncoder();
      const mock_bytes = encoder.encode('image');
      httpMock.getblob.mockResolvedValueOnce(mock_bytes);

      const result = await service.getNextFrame(
        deviceId,
        Mode.ImageAndInferenceResult,
        'classification',
        abortController.signal,
        undefined,
      );

      expect(httpMock.get).toHaveBeenCalledTimes(2);
      expect(httpMock.getblob).toHaveBeenCalled();

      const expected_result: DeviceFrame = {
        image:
          'data:image/jpeg;base64,' + service.arrayBufferToBase64(mock_bytes),
        inference: mock_inf_classification,
        identifier: name,
      };

      expect(result).toStrictEqual(expected_result);
    });

    it('should return device frame if mode json and inference correct object', async () => {
      //mock inference returned by endpoint
      const mock_inf_classification = [
        { class_id: 3, score: 0.351562 },
        { class_id: 1, score: 0.214844 },
        { class_id: 4, score: 0.1875 },
        { class_id: 0, score: 0.167969 },
        { class_id: 2, score: 0.078125 },
      ];
      const deviceId = '123';
      const inferenceResult = {
        Inferences: [{ T: name, F: 1, O: mock_inf_classification }],
      };
      const mockResponse = {
        data: [
          {
            id: name,
            inference: { id: name_inf, inference_result: inferenceResult },
            image: { name: name_img, sas_url: name_img },
          },
        ],
        continuation_token: 'TOKEN1',
      };
      httpMock.get.mockResolvedValueOnce(mockResponse);

      const encoder = new TextEncoder();
      const mock_bytes = encoder.encode('image');
      httpMock.getblob.mockResolvedValueOnce(mock_bytes);

      const result = await service.getNextFrame(
        deviceId,
        Mode.ImageAndInferenceResult,
        'classification',
        abortController.signal,
        undefined,
      );

      expect(httpMock.get).toHaveBeenCalledTimes(1);
      expect(httpMock.getblob).toHaveBeenCalled();

      let expected_class_inf: Classification = {
        perception: { classification_list: [] },
      };
      if (mock_inf_classification.every(isClassificationItem)) {
        expected_class_inf.perception.classification_list =
          mock_inf_classification;
      }
      expected_class_inf.perception.classification_list.forEach((entry) => {
        entry.score = Math.round(entry.score * 100 * 100) / 100;
      });
      const partial_expected_result: DeviceFrame = {
        image:
          'data:image/jpeg;base64,' + service.arrayBufferToBase64(mock_bytes),
        inference: expected_class_inf,
        identifier: name,
      };

      expect(result).toMatchObject(partial_expected_result);
    });

    it('should return device frame if mode json and inference correct string', async () => {
      //mock inference returned by endpoint
      const mock_inf_classification = `[
            { "class_id": 3, "score": 0.351562 },
            { "class_id": 1, "score": 0.214844 },
            { "class_id": 4, "score": 0.1875 },
            { "class_id": 0, "score": 0.167969 },
            { "class_id": 2, "score": 0.078125 }
          ]`;

      const inferenceResult = {
        Inferences: [{ T: name, F: 1, O: mock_inf_classification }],
      };
      const mockResponse = {
        data: [
          {
            id: name,
            inference: { id: name_inf, inference_result: inferenceResult },
            image: { name: name_img, sas_url: name_img },
          },
        ],
        continuation_token: 'TOKEN1',
      };
      httpMock.get.mockResolvedValueOnce(mockResponse);

      const encoder = new TextEncoder();
      const mock_bytes = encoder.encode('image');
      httpMock.getblob.mockResolvedValueOnce(mock_bytes);

      const result = await service.getNextFrame(
        deviceId,
        Mode.ImageAndInferenceResult,
        'classification',
        abortController.signal,
        undefined,
      );

      expect(httpMock.get).toHaveBeenCalledTimes(1);
      expect(httpMock.getblob).toHaveBeenCalled();

      let expected_class_inf: Classification = {
        perception: { classification_list: [] },
      };
      if (JSON.parse(mock_inf_classification).every(isClassificationItem)) {
        expected_class_inf.perception.classification_list = JSON.parse(
          mock_inf_classification,
        );
      }
      expected_class_inf.perception.classification_list.forEach((entry) => {
        entry.score = Math.round(entry.score * 100 * 100) / 100;
      });
      const partial_expected_result: DeviceFrame = {
        image:
          'data:image/jpeg;base64,' + service.arrayBufferToBase64(mock_bytes),
        inference: expected_class_inf,
        identifier: 'NAME1',
      };

      expect(result).toMatchObject(partial_expected_result);
    });

    it('should return device frame if mode json and inference correct string, detection', async () => {
      //mock inference returned by endpoint
      const mock_inf_detection = [
        {
          class_id: 0,
          score: 0.546875,
          bounding_box: { left: 96, top: 5, right: 178, bottom: 136 },
        },
        {
          class_id: 0,
          score: 0.36328125,
          bounding_box: { left: 2, top: 86, right: 33, bottom: 143 },
        },
      ];
      const inferenceResult = {
        Inferences: [{ T: name, F: 1, O: mock_inf_detection }],
      };
      const mockResponse = {
        data: [
          {
            id: name,
            inference: { id: name_inf, inference_result: inferenceResult },
            image: { name: name_img, sas_url: name_img },
          },
        ],
        continuation_token: 'TOKEN1',
      };
      httpMock.get.mockResolvedValueOnce(mockResponse);

      const encoder = new TextEncoder();
      const mock_bytes = encoder.encode('image');
      httpMock.getblob.mockResolvedValueOnce(mock_bytes);

      const result = await service.getNextFrame(
        deviceId,
        Mode.ImageAndInferenceResult,
        'detection',
        abortController.signal,
        undefined,
      );

      expect(httpMock.get).toHaveBeenCalledTimes(1);
      expect(httpMock.getblob).toHaveBeenCalled();

      let expected_det_inf: Detection = {
        perception: { object_detection_list: [] },
      };
      if (mock_inf_detection.every(isDetectionItem)) {
        expected_det_inf.perception.object_detection_list = mock_inf_detection;
      }
      expected_det_inf.perception.object_detection_list.forEach((entry) => {
        entry.score = Math.round(entry.score * 100 * 100) / 100;
      });
      const partial_expected_result: DeviceFrame = {
        image:
          'data:image/jpeg;base64,' + service.arrayBufferToBase64(mock_bytes),
        inference: expected_det_inf,
        identifier: 'NAME1',
      };

      expect(result).toMatchObject(partial_expected_result);
    });

    it('should return ErrorInference if mode json and inference incorrect', async () => {
      //mock inference returned by endpoint
      const mock_inf_classification = `This is not a json`;
      const deviceId = '123';
      const inferenceResult = {
        Inferences: [{ T: 'NAME1', F: 1, O: mock_inf_classification }],
      };
      const mockResponse = {
        data: [
          {
            id: name,
            inference: { id: name_inf, inference_result: inferenceResult },
            image: { name: name_img, sas_url: name_img },
          },
        ],
        continuation_token: 'TOKEN1',
      };
      httpMock.get.mockResolvedValueOnce(mockResponse);

      const encoder = new TextEncoder();
      const mock_bytes = encoder.encode('image');
      httpMock.getblob.mockResolvedValueOnce(mock_bytes);

      const result = await service.getNextFrame(
        deviceId,
        Mode.ImageAndInferenceResult,
        'classification',
        abortController.signal,
        undefined,
      );

      expect(httpMock.get).toHaveBeenCalledTimes(1);

      const errorInference: ErrorInference = {
        errorLabel:
          'Unable to parse metadata contents. Only UTF-8 encoded JSON is supported. Please contact Edge App supplier for more information.',
      };

      const partial_expected_result: DeviceFrame = {
        image:
          'data:image/jpeg;base64,' + service.arrayBufferToBase64(mock_bytes),
        inference: errorInference,
        identifier: 'NAME1',
      };

      expect(result).toMatchObject(partial_expected_result);
    });

    it('should return UnknownInferenceFormatError if mode json and json but not inference', async () => {
      //mock inference returned by endpoint
      const mock_inf_classification = `{}`;

      const inferenceResult = {
        Inferences: [{ T: name, F: 1, O: mock_inf_classification }],
      };
      const mockResponse = {
        data: [
          {
            id: name,
            inference: { id: name_inf, inference_result: inferenceResult },
            image: { name: name_img, sas_url: name_img },
          },
        ],
        continuation_token: 'TOKEN1',
      };
      httpMock.get.mockResolvedValueOnce(mockResponse);

      const encoder = new TextEncoder();
      const mock_bytes = encoder.encode('image');
      httpMock.getblob.mockResolvedValueOnce(mock_bytes);

      const result = await service.getNextFrame(
        deviceId,
        Mode.ImageAndInferenceResult,
        'classification',
        abortController.signal,
        undefined,
      );

      expect(httpMock.get).toHaveBeenCalledTimes(1);

      expect(result).toBeInstanceOf(Error);
      expect((result as Error).message).toBe('INFERENCE_FORMAT');
    });

    it('should return aborted error if already aborted', async () => {
      abortController.abort();
      const result = await service.getNextFrame(
        deviceId,
        Mode.ImageAndInferenceResult,
        'classification',
        abortController.signal,
        undefined,
      );
      expect(result).toBeInstanceOf(Error);
      expect((result as Error).message).toBe('ABORTED');
    });

    it.each([
      Mode.ImageOnly,
      ExtendedMode.Preview,
      'InvalidMode' as unknown as Mode,
    ])(
      "should return error if unsupported mode '%s' is passed",
      async (invalidMode) => {
        const result = await service.getNextFrame(
          deviceId,
          invalidMode,
          'classification',
          abortController.signal,
          undefined,
        );
        expect(result).toBeInstanceOf(Error);
        expect((result as Error).message).toBe(
          `Mode ${invalidMode} not supported`,
        );
      },
    );

    it('should return custom inference as-is if mode is InferenceResult', async () => {
      // Given
      const custom_inference = [
        {
          class_id: 0,
          score: 0.546875,
          key_points: [0, 1, 4],
        },
        {
          class_id: 0,
          score: 0.36328125,
          key_points: [0, 3, 5],
        },
      ];
      const inferenceResult = {
        Inferences: [{ T: name, F: 1, O: custom_inference }],
      };
      const mockResponse = {
        data: [
          {
            id: name,
            inference: { id: name_inf, inference_result: inferenceResult },
            image: { name: name_img, sas_url: name_img },
          },
        ],
        continuation_token: 'TOKEN1',
      };
      httpMock.get.mockResolvedValueOnce(mockResponse);

      const encoder = new TextEncoder();
      const mock_bytes = encoder.encode('image');
      httpMock.getblob.mockResolvedValueOnce(mock_bytes);

      // When
      const result = await service.getNextFrame(
        deviceId,
        Mode.InferenceResult,
        'custom',
        abortController.signal,
        undefined,
      );

      // Then
      expect(httpMock.get).toHaveBeenCalledTimes(1);
      expect(httpMock.getblob).toHaveBeenCalled();

      const partial_expected_result: DeviceFrame = {
        image:
          'data:image/jpeg;base64,' + service.arrayBufferToBase64(mock_bytes),
        inference: custom_inference,
        identifier: 'NAME1',
      };

      expect(result).toMatchObject(partial_expected_result);
    });

    it('should unmarshall custom inference then return if mode is InferenceResult', async () => {
      // Given
      const custom_inference = [
        {
          class_id: 0,
          score: 0.546875,
          key_points: [0, 1, 4],
        },
        {
          class_id: 0,
          score: 0.36328125,
          key_points: [0, 3, 5],
        },
      ];
      const inferenceResult = {
        Inferences: [{ T: name, F: 1, O: JSON.stringify(custom_inference) }],
      };
      const mockResponse = {
        data: [
          {
            id: name,
            inference: { id: name_inf, inference_result: inferenceResult },
            image: { name: name_img, sas_url: name_img },
          },
        ],
        continuation_token: 'TOKEN1',
      };
      httpMock.get.mockResolvedValueOnce(mockResponse);

      const encoder = new TextEncoder();
      const mock_bytes = encoder.encode('image');
      httpMock.getblob.mockResolvedValueOnce(mock_bytes);

      // When
      const result = await service.getNextFrame(
        deviceId,
        Mode.InferenceResult,
        'custom',
        abortController.signal,
        undefined,
      );

      // Then
      expect(httpMock.get).toHaveBeenCalledTimes(1);
      expect(httpMock.getblob).toHaveBeenCalled();

      const partial_expected_result: DeviceFrame = {
        image:
          'data:image/jpeg;base64,' + service.arrayBufferToBase64(mock_bytes),
        inference: custom_inference,
        identifier: 'NAME1',
      };

      expect(result).toMatchObject(partial_expected_result);
    });

    it('should return error  if custom inference and format is NOT Json', async () => {
      // Given
      const custom_inference = [
        {
          class_id: 0,
          score: 0.546875,
          key_points: [0, 1, 4],
        },
        {
          class_id: 0,
          score: 0.36328125,
          key_points: [0, 3, 5],
        },
      ];
      const inferenceResult = {
        Inferences: [{ T: name, F: 0, O: JSON.stringify(custom_inference) }],
      };
      const mockResponse = {
        data: [
          {
            id: name,
            inference: { id: name_inf, inference_result: inferenceResult },
            image: { name: name_img, sas_url: name_img },
          },
        ],
        continuation_token: 'TOKEN1',
      };
      httpMock.get.mockResolvedValueOnce(mockResponse);

      const encoder = new TextEncoder();
      const mock_bytes = encoder.encode('image');
      httpMock.getblob.mockResolvedValueOnce(mock_bytes);

      // When
      const result = await service.getNextFrame(
        deviceId,
        Mode.InferenceResult,
        'custom',
        abortController.signal,
        undefined,
      );

      // Then
      const errorInference: ErrorInference = {
        errorLabel: `Only JSON allowed for Custom Operation Mode (Flatbuffer detected in the inferences)`,
      };

      const partial_expected_result: DeviceFrame = {
        image:
          'data:image/jpeg;base64,' + service.arrayBufferToBase64(mock_bytes),
        inference: errorInference,
        identifier: 'NAME1',
      };

      expect(result).toMatchObject(partial_expected_result);
    });
  });
});
