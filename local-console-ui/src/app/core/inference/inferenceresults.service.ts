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

import { HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { EnvService } from '../common/environment.service';
import { HttpApiClient } from '../common/http/http';
import { OperationMode } from '../device/configuration';
import { DeviceFrame } from '../device/device';
import { DeviceStreamProvider } from '../device/device-visualizer/device-stream-provider';
import { getRandomColorOklch } from '../drawing/color';
import { Point2D } from '../drawing/drawing';
import { ModuleConfigService } from '../module/module-config.service';
import {
  Classification,
  CustomInference,
  Detection,
  ErrorInference,
  ExtendedMode,
  InferenceData,
  InferenceItem,
  InferenceLike,
  Inferences,
  isClassificationInference,
  isDetectionInference,
  isErrorInference,
  Mode,
  TaskType,
} from './inference';
import {
  isClassificationItem,
  isDetectionItem,
} from './inferenceresults.utils';

export const ALLOWED_MODES: Array<Mode | ExtendedMode> = [
  Mode.ImageAndInferenceResult,
  Mode.InferenceResult,
];
export const PROCESS_STATE_RUNNING = 2;
export const PROCESS_STATE_IDLE = 1;
// TODO: This id should be explored properly
export const PERMANENT_MODULE_ID = 'node';
export const ABORTED = new Error('ABORTED');

export class AbortedError extends Error {
  constructor(message?: string) {
    super(message ?? 'ABORTED');
  }
}

export class UnknownInferenceFormatError extends Error {
  constructor(message?: string) {
    super(message ?? 'INFERENCE_FORMAT');
  }
}

export interface ImageDescriptor {
  name: string;
  sas_url: string;
}

export interface Images {
  data: ImageDescriptor[];
  continuation_token: string | null;
}
export interface InferenceImagePairs {
  data: InferenceImagePairItem[];
  continuation_token: string | null;
}
export interface InferenceImagePairItem {
  id: string;
  inference: InferenceData;
  image: ImageDescriptor;
}

export const TaskTypeOperationsModeMap = {
  [TaskType.Classification]: ['classification', 'generic_classification'],
  [TaskType.ObjectDetection]: ['detection', 'generic_detection'],
  [TaskType.Custom]: ['custom'],
};

@Injectable({
  providedIn: 'root',
})
export class InferenceResultsService implements DeviceStreamProvider {
  constructor(
    private http: HttpApiClient,
    private properties: ModuleConfigService,
    private envService: EnvService,
  ) {}

  get inferencePath() {
    return `${this.envService.getApiUrl()}/inferenceresults/devices`;
  }

  get imagePath() {
    return `${this.envService.getApiUrl()}/images/devices`;
  }

  async getLastInference(device_id: string, lastIdentifier?: string) {
    const response = await this.http.get<Inferences>(
      `${this.inferencePath}/${device_id}?limit=1`,
      {},
      false,
    );

    const inferenceResult = response?.data?.[0]?.inference_result;
    const identifier = inferenceResult?.Inferences?.[0]?.T;

    if (!inferenceResult || !identifier) {
      throw new Error('Invalid response structure');
    }

    if (lastIdentifier === identifier) {
      throw new Error('No new images found for this device');
    }

    return { inferenceResult, identifier };
  }

  async init(
    device_id: string,
    roiOffset: Point2D,
    roiSize: Point2D,
    mode: Mode | ExtendedMode,
  ) {
    if (!ALLOWED_MODES.includes(mode))
      throw new Error('Incorrect mode for Inference Results provider');
    await this.properties.patchModuleConfiguration(
      device_id,
      PERMANENT_MODULE_ID,
      {
        common_settings: {
          process_state: PROCESS_STATE_RUNNING,
          pq_settings: {
            image_cropping: {
              left: roiOffset.x,
              top: roiOffset.y,
              width: roiSize.x,
              height: roiSize.y,
            },
          },
          port_settings: {
            metadata: {
              enabled: true,
            },
            input_tensor: {
              enabled: true,
            },
          },
        },
      },
    );
  }

  async teardown(device_id: string) {
    await this.properties.patchModuleConfiguration(
      device_id,
      PERMANENT_MODULE_ID,
      {
        common_settings: {
          port_settings: {
            metadata: {
              enabled: false,
            },
            input_tensor: {
              enabled: false,
            },
          },
        },
      },
    );
  }

  async getNextFrame(
    device_id: string,
    mode: Mode | ExtendedMode,
    expectedType: OperationMode,
    abortSignal: AbortSignal,
    lastFrame: DeviceFrame | undefined,
  ): Promise<DeviceFrame | Error> {
    try {
      if (abortSignal.aborted) return ABORTED;
      if (!ALLOWED_MODES.includes(mode))
        return new Error(`Mode ${mode} not supported`);

      const latestPair = await this.getLatestPair(
        device_id,
        lastFrame?.identifier,
      );
      if (abortSignal.aborted) return ABORTED;

      const identifier = latestPair.id;
      if (identifier === lastFrame?.identifier) {
        return new Error('No new frame available');
      }

      const image = await this.getImageByName(device_id, latestPair.image.name);
      const infDef = latestPair.inference.inference_result?.Inferences?.[0];
      if (!infDef) throw new Error('Missing inference data');

      const parsedInference = await this.getInferenceData(
        device_id,
        infDef.O,
        !!infDef.F,
        abortSignal,
        mode,
        expectedType,
      );

      if (parsedInference instanceof Error) return parsedInference;
      if (abortSignal.aborted) return ABORTED;

      const finalInference = this.checkTaskTypeOperationModeMatch(
        infDef.P,
        expectedType,
        parsedInference,
      );

      return { image, inference: finalInference, identifier };
    } catch (error) {
      console.error(error);
      return new Error('Cannot get device frame');
    }
  }

  async getLatestPair(
    device_id: string,
    lastIdentifier?: string,
  ): Promise<InferenceImagePairItem> {
    const response = await this.http.get<InferenceImagePairs>(
      `${this.inferencePath}/${device_id}/withimage?limit=1`,
      {},
      false,
    );

    const inferenceResult = response?.data?.[0]?.inference.inference_result;
    const identifier = inferenceResult?.Inferences?.[0]?.T;

    if (!inferenceResult || !identifier) {
      throw new Error('Invalid response structure');
    }
    // TODO: handle when `lastIdentifier === identifier`

    return response.data[0];
  }

  async getInferenceData(
    device_id: string,
    rawData: any,
    formatIsJson: boolean,
    abortSignal: AbortSignal,
    mode: Mode | ExtendedMode,
    expectedType: OperationMode,
  ) {
    let parsedInference: InferenceLike | Error;

    if (!formatIsJson) {
      if (expectedType == 'custom') {
        return <ErrorInference>{
          errorLabel: `Only JSON allowed for Custom Operation Mode (Flatbuffer detected in the inferences)`,
        };
      } else {
        parsedInference = await this.convertToJson(device_id, rawData);
      }
      if (abortSignal.aborted) return ABORTED;
    } else {
      parsedInference = this.getInferenceFromJSONLiteral(
        rawData,
        mode,
        expectedType,
      );
    }

    if (parsedInference instanceof Error) return parsedInference;

    if (
      mode === Mode.ImageAndInferenceResult &&
      !isErrorInference(parsedInference)
    ) {
      return this.processKnownInferences(parsedInference, expectedType);
    }

    return parsedInference;
  }

  getOperationTypeName(operationModeType: OperationMode): OperationMode {
    return <OperationMode>{
      classification: 'classification',
      detection: 'detection',
      generic_classification: 'classification',
      generic_detection: 'detection',
      custom: 'custom',
      image: 'image',
    }[operationModeType];
  }

  checkTaskTypeOperationModeMatch(
    taskType: TaskType | undefined,
    operationMode: OperationMode,
    inference: InferenceLike,
  ): InferenceLike {
    if (isErrorInference(inference)) {
      return inference;
    } else if (
      !taskType ||
      TaskTypeOperationsModeMap[taskType].includes(operationMode)
    ) {
      return inference;
    } else {
      return <ErrorInference>{
        errorLabel: `The task type reported by the application running in the device is ${TaskTypeOperationsModeMap[taskType][0]},
            but ${this.getOperationTypeName(operationMode)} was expected for the given Operation Mode.`,
      };
    }
  }

  getInferenceFromJSONLiteral(
    rawData: any,
    mode: Mode | ExtendedMode,
    expectedType: OperationMode,
  ) {
    let partialInference: Object[] = [];
    if (typeof rawData === 'string') {
      try {
        partialInference = JSON.parse(rawData);
      } catch (error) {
        console.warn(error);
        return <ErrorInference>{
          errorLabel:
            'Unable to parse metadata contents. Only UTF-8 encoded JSON is supported. Please contact Edge App supplier for more information.',
        };
      }
    } else {
      partialInference = rawData;
    }
    if (expectedType !== 'custom' && !Array.isArray(partialInference)) {
      return new UnknownInferenceFormatError();
    }
    return this.completeJson(partialInference, expectedType);
  }

  processKnownInferences(
    inference: Classification | Detection | CustomInference,
    expectedType: OperationMode,
  ) {
    let hits: InferenceItem[] = [];

    switch (expectedType) {
      case 'detection':
      case 'generic_detection':
        if (isDetectionInference(inference)) {
          this.fillInInferenceData(inference.perception.object_detection_list);
          return inference;
        }
        break;
      case 'classification':
      case 'generic_classification':
        if (isClassificationInference(inference)) {
          this.fillInInferenceData(inference.perception.classification_list);
          return inference;
        }
        break;
      default: // really just 'custom', 'image' should never be here...
        return <CustomInference>inference;
    }
    return new UnknownInferenceFormatError();
  }

  async convertToJson(device_id: string, flatbuffer_payload: string) {
    let queryParams = new HttpParams();
    queryParams = queryParams.append('flatbuffer_payload', flatbuffer_payload);
    return await this.http
      .get<InferenceLike>(
        `${this.inferencePath}/${device_id}/json`,
        queryParams,
        false,
      )
      .catch((err) => {
        return <ErrorInference>{
          errorLabel: `Error happened in the conversion of the flatbuffer: ${err.error.message}`,
        };
      });
  }

  completeJson(
    partialInference: Object[],
    expectedType: OperationMode,
  ): InferenceLike {
    switch (expectedType) {
      case 'detection':
      case 'generic_detection':
        if (partialInference.every(isDetectionItem)) {
          let detection: Detection = {
            perception: { object_detection_list: [] },
          };
          detection.perception.object_detection_list = partialInference;
          return detection;
        }
        break;
      case 'classification':
      case 'generic_classification':
        if (partialInference.every(isClassificationItem)) {
          let classification: Classification = {
            perception: { classification_list: [] },
          };
          classification.perception.classification_list = partialInference;
          return classification;
        }
        break;
      default: // really just 'custom', 'image' should never be here...
        return <CustomInference>partialInference;
    }
    return new UnknownInferenceFormatError();
  }

  async getImageByName(device_id: string, name: string) {
    const bytes = await this.http.getblob(
      `${this.imagePath}/${device_id}/image/${name}`,
      undefined,
      false,
    );
    return 'data:image/jpeg;base64,' + this.arrayBufferToBase64(bytes);
  }

  async getImageBySasUrl(sasUrl: string) {
    const bytes = await this.http.getblob(
      `${this.envService.getApiUrl()}${sasUrl}`,
      undefined,
      false,
    );
    return 'data:image/jpeg;base64,' + this.arrayBufferToBase64(bytes);
  }

  async getLatestImageDescriptor(device_id: string, lastIdentifier?: string) {
    const response = await this.http.get<Images>(
      `${this.imagePath}/${device_id}/directories?limit=1`,
      {},
      false,
    );

    const latestImage = response?.data?.[0];

    if (!latestImage || !latestImage.name || !latestImage.sas_url) {
      throw new Error('Invalid response structure');
    }

    if (lastIdentifier === latestImage.name) {
      throw new Error('No new images found for this device');
    }

    return {
      name: latestImage.name,
      identifier: latestImage.name,
      sasUrl: latestImage.sas_url,
    };
  }

  private fillInInferenceData(hits: InferenceItem[]) {
    // Reset random for consistent colors
    hits.forEach((item) => {
      item.score = Math.round(item.score * 100 * 100) / 100;
      item.color = getRandomColorOklch(item.class_id);
      item.label = 'Class ' + item.class_id;
    });
  }

  public arrayBufferToBase64(buffer: ArrayBuffer): string {
    const uint8Array = new Uint8Array(buffer);

    let binaryString = '';
    for (let i = 0; i < uint8Array.length; i++) {
      binaryString += String.fromCharCode(uint8Array[i]);
    }

    return btoa(binaryString);
  }
}
