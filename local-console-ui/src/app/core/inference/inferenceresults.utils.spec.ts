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

import { isClassification, isDetection } from './inferenceresults.utils';

describe('Check types', () => {
  describe('isClassification', () => {
    it('should return true for valid classification data', () => {
      const validClassification = {
        perception: {
          classification_list: [
            { class_id: 0, score: 0.95 },
            { class_id: 1, score: 0.85 },
          ],
        },
      };
      expect(isClassification(validClassification)).toBe(true);
    });

    it('should return false if classification_list is missing', () => {
      const invalidClassification = {
        perception: {
          // missing classification_list
        },
      };
      expect(isClassification(invalidClassification)).toBe(false);
    });

    it('should return false if class_id or score is not a number', () => {
      const invalidClassification = {
        perception: {
          classification_list: [
            { class_id: '0', score: 0.5 }, // class_id is string, not number
          ],
        },
      };
      expect(isClassification(invalidClassification)).toBe(false);
    });

    it('should return false if the data is null or not an object', () => {
      expect(isClassification(null)).toBe(false);
      expect(isClassification(123)).toBe(false);
      expect(isClassification('some string')).toBe(false);
    });
  });

  describe('isDetection', () => {
    it('should return true for valid detection data', () => {
      const validDetection = {
        perception: {
          object_detection_list: [
            {
              class_id: 0,
              score: 0.9,
              bounding_box_type: 'BoundingBox2d',
              bounding_box: {
                left: 0,
                top: 10,
                right: 100,
                bottom: 200,
              },
            },
          ],
        },
      };
      expect(isDetection(validDetection)).toBe(true);
    });

    it('should return false if object_detection_list is missing', () => {
      const invalidDetection = {
        perception: {
          // Missing object_detection_list
        },
      };
      expect(isDetection(invalidDetection)).toBe(false);
    });

    it('should return false if bounding_box is invalid', () => {
      const invalidDetection = {
        perception: {
          object_detection_list: [
            {
              class_id: 1,
              score: 0.75,
              bounding_box_type: 'BoundingBox2d',
              bounding_box: null, // not an object
            },
          ],
        },
      };
      expect(isDetection(invalidDetection)).toBe(false);
    });

    it('should return false if any bounding_box coordinates are not numbers', () => {
      const invalidDetection = {
        perception: {
          object_detection_list: [
            {
              class_id: 1,
              score: 0.75,
              bounding_box_type: 'BoundingBox2d',
              bounding_box: {
                left: 0,
                top: '10', // string instead of number
                right: 100,
                bottom: 200,
              },
            },
          ],
        },
      };
      expect(isDetection(invalidDetection)).toBe(false);
    });

    it('should return false if data is null or not an object', () => {
      expect(isDetection(null)).toBe(false);
      expect(isDetection(123)).toBe(false);
      expect(isDetection('some string')).toBe(false);
    });
  });
});
