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

import { Box, Point2D } from './drawing';
import { SurfaceMode } from './drawing-surface.component';
import { Scene } from './scene';
import { Surface } from './surface';

export class Controls {
  private __mode: SurfaceMode = 'render';
  roiBox?: Box;
  private mouseCapture?: Point2D;

  constructor(
    private surface: Surface,
    private scene: Scene,
  ) {}

  get mode() {
    return this.__mode;
  }
  set mode(newMode: SurfaceMode) {
    this.__mode = newMode;
    delete this.roiBox;
    delete this.mouseCapture;
  }

  mouseDown(evt: MouseEvent) {
    if (this.mode === 'render' || !this.scene.drawing) return;

    delete this.roiBox;
    const mouseCoords = this.getMousePos(evt);
    if (this.scene.drawing.boundary.isPointInside(mouseCoords)) {
      this.mouseCapture = mouseCoords;
    }
  }

  mouseMove(evt: MouseEvent) {
    if (this.mode === 'render' || !this.mouseCapture || !this.scene.drawing)
      return;

    const subBoundaryMin = this.scene.drawing.boundary.min.mul(-1);
    const reverseScale = 1 / this.scene.drawing.scale;
    this.roiBox = new Box(this.mouseCapture, this.getMousePos(evt))
      .clamp(this.scene.drawing.boundary)
      .add(subBoundaryMin)
      .mul(reverseScale);
  }

  mouseUp(evt: MouseEvent) {
    delete this.mouseCapture;
  }

  private getMousePos(evt: MouseEvent) {
    var rect = this.surface.getOffset();
    return new Point2D(evt.clientX - rect.x, evt.clientY - rect.y);
  }
}
