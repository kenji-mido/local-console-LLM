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

export enum Mode {
  ImageOnly = 0,
  ImageAndInferenceResult = 1,
  InferenceResult = 2,
}

/* Inference example:
{
  "data": [
    {
      "id": "20241025170515813.txt",
      "model_id": "0300009999990100",
      "model_version_id": "",
      "inference_result": {
        "DeviceID": "Aid-00010001-0000-2000-9002-0000000001d1",
        "ModelID": "0300009999990100",
        "Image": true,
        "Inferences": [
          {
            "T": "20241025170515813",
            "O": "AAAwvgAAID4AAOA9AAAAvQAA4D0AAEC+AACwvgAAkD4AADA+AACAvg=="
          }
        ]
      }
    }
  ],
  "continuation_token": null
}
*/
export interface InferenceDataResultInference {
  T: string;
  O: string;
}
export interface InferenceDataResult {
  DeviceID: string;
  ModelID: string;
  Image: boolean;
  Inferences: InferenceDataResultInference[];
}
export interface InferenceData {
  id: string;
  model_id: string;
  model_version_id: string;
  inference_result: InferenceDataResult;
}
export interface Inference {
  data: InferenceData[];
  continuation_token: string | null;
}

export interface InferenceItem {
  class_id: number;
  score: number;
  label: string;
  // new
  color: [number, number, number];
}

/* Example of JSON classification,
"perception": {
    "classification_list": [
        {"class_id": 3, "score": 0.351562},
        {"class_id": 1, "score": 0.214844},
        {"class_id": 4, "score": 0.1875},
        {"class_id": 0, "score": 0.167969},
        {"class_id": 2, "score": 0.078125},
    ]
}
*/
export interface ClassificationItem extends InferenceItem {}
export interface ClassificationPerception {
  classification_list: ClassificationItem[];
}
export interface Classification {
  perception: ClassificationPerception;
}

/* Example of JSON detection,
{
  "perception": {
    "object_detection_list": [
      {
        "class_id": 0,
        "bounding_box_type": "BoundingBox2d",
        "bounding_box": {
          "left": 4,
          "top": 13,
          "right": 170,
          "bottom": 174
        },
        "score": 0.914062
      }
    ]
  }
}
*/
export interface Bbox {
  left: number;
  top: number;
  right: number;
  bottom: number;
}
export interface DetectionItem extends InferenceItem {
  bounding_box_type: string;
  bounding_box: Bbox;
}
export interface DetectionPerception {
  object_detection_list: DetectionItem[];
}
export interface Detection {
  perception: DetectionPerception;
}

export function isClassificationInference(
  inference: Classification | Detection,
): inference is Classification {
  return (
    !!inference.perception &&
    !!(<Classification>inference).perception.classification_list
  );
}
