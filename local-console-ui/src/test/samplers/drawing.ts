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
  Box,
  BoxDrawingElement,
  Drawing,
  LabelDrawingElement,
  NativeImageDrawingElement,
  Point2D,
  ROIBoxDrawingElement,
} from '@app/core/drawing/drawing';

export namespace Drawings {
  export function sample() {
    return <Drawing>{
      scale: 1,
      boundary: new Box(0, 0, 800, 600),
      elements: [sampleNativeImage(), sampleLabel(), sampleBox(), sampleRoi()],
    };
  }

  export function sampleNativeImage() {
    return <NativeImageDrawingElement>{
      type: 'nativeImage',
      img: new Image(),
      offset: new Point2D(0, 0),
      size: new Point2D(100, 100),
    };
  }

  export function sampleLabel() {
    return <LabelDrawingElement>{
      type: 'label',
      text: 'Test Label',
      bgColor: 'white',
      txtColor: 'black',
      position: new Point2D(100, 100),
      fixed: false,
    };
  }

  export function sampleBox() {
    return <BoxDrawingElement>{
      type: 'box',
      min: new Point2D(200, 200),
      max: new Point2D(300, 300),
      color: 'blue',
      width: 2,
    };
  }
  export function sampleRoi() {
    return <ROIBoxDrawingElement>{
      type: 'roiBox',
      box: { min: new Point2D(300, 300), max: new Point2D(400, 400) },
    };
  }
}
