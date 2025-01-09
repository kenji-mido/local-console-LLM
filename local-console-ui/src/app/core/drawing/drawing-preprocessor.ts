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
  Drawing,
  DrawingElement,
  ImageDrawingElement,
  NativeImageDrawingElement,
  Point2D,
  RawDrawing,
} from './drawing';

export async function preprocessDrawing(
  rawDrawing: RawDrawing,
  surfaceDimensions: Point2D,
): Promise<Drawing> {
  const elements = (<DrawingElement[]>[]).concat(rawDrawing.elements);
  const imageAt = rawDrawing.elements.findIndex((el) => el.type === 'image');
  let boundary = new Box(0, 0, 1, 1);
  let scale = 1;
  if (imageAt >= 0) {
    const nativeImage = await preprocessImage(
      <ImageDrawingElement>elements[imageAt],
      surfaceDimensions,
    );
    elements[imageAt] = nativeImage.image;
    boundary = nativeImage.boundary;
    scale = nativeImage.scale;
  }

  return <Drawing>{
    elements,
    boundary,
    scale,
  };
}

async function preprocessImage(
  im: ImageDrawingElement,
  surfaceDimensions: Point2D,
): Promise<{
  boundary: Box;
  scale: number;
  image: NativeImageDrawingElement;
}> {
  const surfaceRatio = surfaceDimensions.x / surfaceDimensions.y;
  let printWidth: number, printHeight: number, top: number, left: number;

  return new Promise((accept) => {
    var img = new Image();
    img.onload = function () {
      const imageRatio = img.naturalWidth / img.naturalHeight;
      if (imageRatio >= surfaceRatio) {
        // Image should be width-bound
        printWidth = surfaceDimensions.x;
        printHeight = printWidth / imageRatio;
        left = 0;
        top = (surfaceDimensions.y - printHeight) / 2;
      } else {
        // Image should be height-bound
        printHeight = surfaceDimensions.y;
        printWidth = printHeight * imageRatio;
        top = 0;
        left = (surfaceDimensions.x - printWidth) / 2;
      }
      accept({
        boundary: new Box(left, top, left + printWidth, top + printHeight),
        scale: printWidth / img.naturalWidth,
        image: <NativeImageDrawingElement>{
          type: 'nativeImage',
          img,
          offset: new Point2D(left, top),
          size: new Point2D(printWidth, printHeight),
        },
      });
      img.onload = () => {};
    };
    img.src = im.data;
  });
}
