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

import { PNG } from 'pngjs';

export function AsSSIMObj(png: PNG) {
  const image_data = {
    data: new Uint8ClampedArray(png.data),
    height: png.height,
    width: png.width,
  };
  return image_data;
}

export function BBoxesForComparison(a: PNG, b: PNG) {
  const min_w = Math.min(a.width, b.width);
  const min_h = Math.min(a.height, b.height);

  const a_min = CropImage(a, min_w, min_h);
  const b_min = CropImage(b, min_w, min_h);
  return [a_min, b_min];
}

export function CropImage(image: PNG, width: number, height: number) {
  // For now, pin cropping bounding box to the default corner
  const x = 0,
    y = 0;

  let subImage = new PNG({ width, height });
  for (let j = 0; j < height; j++) {
    for (let i = 0; i < width; i++) {
      const idxSource = (image.width * (j + y) + (i + x)) << 2;
      const idxDest = (width * j + i) << 2;

      // Copy pixel values
      subImage.data[idxDest] = image.data[idxSource]; // Red
      subImage.data[idxDest + 1] = image.data[idxSource + 1]; // Green
      subImage.data[idxDest + 2] = image.data[idxSource + 2]; // Blue
      subImage.data[idxDest + 3] = image.data[idxSource + 3]; // Alpha
    }
  }
  subImage.pack();
  return subImage;
}
