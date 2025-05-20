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
  BoxDrawingElement,
  BoxLike,
  Drawing,
  LabelDrawingElement,
  NativeImageDrawingElement,
  Point2D,
  ROIBoxDrawingElement,
} from './drawing';
import { Surface } from './surface';

export const LABEL_HEIGHT = 20;
export const ROI_COLOR = 'red';
export const ROI_WIDTH = 3;

export class Scene {
  private __currentDrawing?: Drawing;
  pristine = true;
  get drawing() {
    return this.__currentDrawing;
  }

  constructor(private surface: Surface) {}

  clear() {
    this.surface.ctx?.clearRect(
      0,
      0,
      this.surface.canvas.clientWidth,
      this.surface.canvas.clientHeight,
    );
    this.pristine = true;
  }

  render(drawing: Drawing) {
    this.__currentDrawing = drawing;
    // If image, draw at bottom
    const image = <NativeImageDrawingElement>(
      drawing.elements.find((element) => element.type === 'nativeImage')
    );

    // Pre-wipe
    this.clear();

    if (image) {
      this.drawImage(image.img, image.offset, image.size);
    }
    // Rendering bottom to top
    for (const element of drawing.elements) {
      switch (element.type) {
        case 'label':
          const label = element as LabelDrawingElement;
          this.drawLabel(
            label.text,
            label.bgColor,
            label.txtColor,
            label.position,
            label.fixed,
          );
          break;
        case 'box':
          const box = element as BoxDrawingElement;
          this.drawBox(box.min, box.max, box.color, box.width);
      }
    }

    // Finally, render roiBox, if any
    const roiBox = <ROIBoxDrawingElement>(
      drawing.elements.find((element) => element.type === 'roiBox')
    );
    if (roiBox) {
      this.drawROIBox(roiBox.box);
    }
    this.pristine = false;
  }

  private drawROIBox(roiBox: BoxLike) {
    const offsetPos = new Point2D(3, 3);
    const offsetNeg = offsetPos.mul(-1);
    // Main body
    this.drawBox(roiBox.min, roiBox.max, ROI_COLOR, ROI_WIDTH);
    // Corners
    const corners = [
      roiBox.min,
      roiBox.max,
      new Point2D(roiBox.min.x, roiBox.max.y),
      new Point2D(roiBox.max.x, roiBox.min.y),
    ];
    for (const corner of corners) {
      this.drawBox(
        corner.add(offsetNeg),
        corner.add(offsetPos),
        ROI_COLOR,
        ROI_WIDTH,
      );
    }
  }

  private drawImage(image: HTMLImageElement, offset: Point2D, size: Point2D) {
    if (!this.surface) return;
    this.surface.ctx.drawImage(image, offset.x, offset.y, size.x, size.y);
  }

  private drawLabel(
    text: string,
    bgColor: string,
    txtColor: string,
    position: Point2D,
    fixed: boolean,
  ) {
    if (!this.surface || !this.drawing || !text) return;

    const width = (text.length + 2) * 10;

    // Calculate the top-left corner of the rectangle from the bottom-left position
    const scale = fixed ? 1 : this.drawing.scale;
    const pos = position
      .mul(scale)
      .add(this.drawing.boundary.min)
      .add(0, -LABEL_HEIGHT);

    // Draw the background rectangle
    const ctx = this.surface.ctx;
    ctx.fillStyle = bgColor;
    ctx.fillRect(pos.x, pos.y, width, LABEL_HEIGHT);

    ctx.fillStyle = txtColor;
    ctx.font = '16px monospace'; // Standard monospace font
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';

    const textX = pos.x + 8;
    const textY = pos.y + LABEL_HEIGHT / 2;
    ctx.fillText(text, textX, textY);
  }

  private drawBox(min: Point2D, max: Point2D, color: string, width: number) {
    if (!this.surface || !this.drawing || !min || !max || !width) return;
    const scale = this.drawing.scale;
    const boundary = this.drawing.boundary;
    const ctx = this.surface.ctx;
    ctx.strokeStyle = color;
    ctx.lineWidth = width;

    min = min.mul(scale).add(boundary.min);
    max = max.mul(scale).add(boundary.min);

    const rectX = min.x;
    const rectY = min.y;
    const rectWidth = max.x - min.x;
    const rectHeight = max.y - min.y;

    ctx.beginPath();
    ctx.rect(rectX, rectY, rectWidth, rectHeight);
    ctx.stroke();
  }
}
