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

import { getColorLuminance, getColorString } from '../drawing/color';
import {
  BoxDrawingElement,
  DrawingElement,
  LabelDrawingElement,
  Point2D,
} from '../drawing/drawing';
import { Classification, Detection } from './inference';

export function getDrawingElementsForClassification(
  classification: Classification,
): DrawingElement[] {
  let position = new Point2D(10, 30);
  return classification.perception.classification_list.map((hit) => {
    const drawingElement = <LabelDrawingElement>{
      type: 'label',
      bgColor: getColorString(hit.color),
      text: `${Math.round(hit.score)}%: ${hit.label}`,
      txtColor: Math.round(getColorLuminance(hit.color)) ? 'black' : 'white',
      position: position.clone(),
      fixed: true,
    };
    position = position.add(0, 25);
    return drawingElement;
  });
}

export function getDrawingElementsForDetection(
  detection: Detection,
): DrawingElement[] {
  return detection.perception.object_detection_list.flatMap((hit) => {
    const bb = hit.bounding_box;
    const bgColor = getColorString(hit.color);
    const min = new Point2D(bb.left, bb.top);
    const max = new Point2D(bb.right, bb.bottom);
    const label = <LabelDrawingElement>{
      type: 'label',
      bgColor: bgColor,
      text: `${Math.round(hit.score)}%: ${hit.label}`,
      txtColor: Math.round(getColorLuminance(hit.color)) ? 'black' : 'white',
      position: min.clone(),
      fixed: false,
    };
    const box = <BoxDrawingElement>{
      type: 'box',
      color: bgColor,
      min,
      max,
      width: 2,
    };
    return [label, box];
  });
}

export function colorBytesToHexString(R: number, G: number, B: number) {
  return '#' + [R, G, B].map((n) => numberToPaddedHex(n, 2)).join('');
}

export function colorLuminance(R: number, G: number, B: number) {
  // Standard perceived luminance function
  return 0.299 * R + 0.587 * G + 0.114 * B;
}

export function numberToPaddedHex(n: number, pad: number) {
  const hex = n.toString(16);
  return '0'.repeat(Math.max(pad - hex.length, 0)) + hex;
}
