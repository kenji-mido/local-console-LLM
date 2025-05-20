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

import { Point2D } from './drawing';

export class Surface {
  public readonly ctx: CanvasRenderingContext2D;
  constructor(
    public readonly canvas: HTMLCanvasElement,
    private parent: HTMLElement,
  ) {
    const ctx = canvas.getContext('2d');
    if (!ctx)
      throw new Error(
        'Cannot initialize scene. Rendering Context not available',
      );
    this.ctx = ctx;
  }

  getDimensions() {
    const rect = this.parent.getBoundingClientRect();
    const dimm = new Point2D(rect.width, rect.height);
    const styles = getComputedStyle(this.canvas);
    const pad = new Point2D(
      parseFloat(styles.paddingLeft) + parseFloat(styles.paddingRight),
      parseFloat(styles.paddingTop) + parseFloat(styles.paddingBottom),
    );
    const finalDimensions = dimm.add(pad.mul(-1)).round();
    if (this.canvas.width !== finalDimensions.x)
      this.canvas.width = finalDimensions.x;
    if (this.canvas.height !== finalDimensions.y)
      this.canvas.height = finalDimensions.y;
    return finalDimensions;
  }

  getOffset() {
    const rect = this.parent.getBoundingClientRect();
    const offset = new Point2D(rect.left, rect.top);
    const styles = getComputedStyle(this.canvas);
    const pad = new Point2D(
      parseFloat(styles.paddingLeft),
      parseFloat(styles.paddingTop),
    );
    return offset.add(pad);
  }
}
