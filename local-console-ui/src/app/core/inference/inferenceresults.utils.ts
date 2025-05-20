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
  DetectionItem,
} from './inference';

export function isClassification(obj: unknown): obj is Classification {
  if (typeof obj !== 'object' || obj === null) {
    return false;
  }

  const { perception } = obj as { perception?: unknown };
  if (typeof perception !== 'object' || perception === null) {
    return false;
  }

  const { classification_list } = perception as {
    classification_list?: unknown;
  };
  if (!Array.isArray(classification_list)) {
    return false;
  }

  return classification_list.every(
    (item) =>
      item &&
      typeof item === 'object' &&
      typeof item.class_id === 'number' &&
      typeof item.score === 'number',
  );
}

export function isClassificationItem(obj: unknown): obj is ClassificationItem {
  if (typeof obj !== 'object' || obj === null) {
    return false;
  }

  const { class_id, score } = obj as {
    class_id?: unknown;
    score?: unknown;
  };

  return typeof class_id === 'number' && typeof score === 'number';
}

export function isDetection(obj: unknown): obj is Detection {
  if (typeof obj !== 'object' || obj === null) {
    return false;
  }

  const { perception } = obj as { perception?: unknown };
  if (typeof perception !== 'object' || perception === null) {
    return false;
  }

  const { object_detection_list } = perception as {
    object_detection_list?: unknown;
  };
  if (!Array.isArray(object_detection_list)) {
    return false;
  }

  return object_detection_list.every((item) => {
    if (!item || typeof item !== 'object') {
      return false;
    }

    const { class_id, score, bounding_box_type, bounding_box } = item as {
      class_id?: unknown;
      score?: unknown;
      bounding_box_type?: unknown;
      bounding_box?: unknown;
    };

    if (typeof class_id !== 'number' || typeof score !== 'number') {
      return false;
    }

    if (typeof bounding_box !== 'object' || bounding_box === null) {
      return false;
    }

    const { left, top, right, bottom } = bounding_box as {
      left?: unknown;
      top?: unknown;
      right?: unknown;
      bottom?: unknown;
    };

    return (
      typeof left === 'number' &&
      typeof top === 'number' &&
      typeof right === 'number' &&
      typeof bottom === 'number'
    );
  });
}

export function isDetectionItem(obj: unknown): obj is DetectionItem {
  if (typeof obj !== 'object' || obj === null) {
    return false;
  }

  const { class_id, score, bounding_box } = obj as {
    class_id?: unknown;
    score?: unknown;
    bounding_box?: unknown;
  };

  if (typeof class_id !== 'number' || typeof score !== 'number') {
    return false;
  }

  if (typeof bounding_box !== 'object' || bounding_box === null) {
    return false;
  }

  const { left, top, right, bottom } = bounding_box as {
    left?: unknown;
    top?: unknown;
    right?: unknown;
    bottom?: unknown;
  };

  return (
    typeof left === 'number' &&
    typeof top === 'number' &&
    typeof right === 'number' &&
    typeof bottom === 'number'
  );
}
