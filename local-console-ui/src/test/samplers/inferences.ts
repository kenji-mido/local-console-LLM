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
  Classification,
  ClassificationItem,
  Detection,
} from '@app/core/inference/inference';

export type InferenceType = 'classification' | 'detection';

export namespace Inferences {
  export function sample(type: InferenceType) {
    switch (type) {
      case 'classification':
        return <Classification>{
          perception: {
            classification_list: [0, 1, 2].map((i) => Inferences.sampleItem(i)),
          },
        };
      case 'detection':
      default:
        return <Detection>{
          perception: {
            object_detection_list: [0, 1, 2].map((i) =>
              Inferences.sampleItem(i),
            ),
          },
        };
    }
  }

  export function sampleItem(class_id: number) {
    const score = 0.2 * class_id;
    const col = Math.round(127 * score);
    return <ClassificationItem>{
      class_id,
      label: 'Class ' + class_id,
      score: score,
      color: [col * 0.6, col * 0.8, col],
    };
  }
}
