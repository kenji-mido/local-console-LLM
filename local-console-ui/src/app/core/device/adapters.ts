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
  DrawingElement,
  ImageDrawingElement,
  RawDrawing,
} from '../drawing/drawing';
import {
  getDrawingElementsForClassification,
  getDrawingElementsForDetection,
} from '../inference/drawing-adapter';
import {
  isClassificationInference,
  isDetectionInference,
} from '../inference/inference';
import { DeviceFrame } from './device';

export function toDrawing(frame: DeviceFrame) {
  const elements: DrawingElement[] = [];
  elements.push(<ImageDrawingElement>{
    type: 'image',
    data: frame.image,
  });
  if (frame.inference) {
    if (isClassificationInference(frame.inference)) {
      elements.push(...getDrawingElementsForClassification(frame.inference));
    } else if (isDetectionInference(frame.inference)) {
      elements.push(...getDrawingElementsForDetection(frame.inference));
    }
    // else if custom, we already have the image and that's all we draw
  }
  return <RawDrawing>{ elements };
}
