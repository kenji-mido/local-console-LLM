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

export type SurfaceMode = 'render' | 'capture';

import {
  AfterViewInit,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnDestroy,
  Output,
} from '@angular/core';
import { Controls } from './controls';
import { BoxLike, Drawing, RawDrawing, ROIBoxDrawingElement } from './drawing';
import { preprocessDrawing } from './drawing-preprocessor';
import { Scene } from './scene';
import { Surface } from './surface';

export enum DrawingState {
  Error = 0,
  Streaming = 1,
  Disabled = 2,
}

@Component({
  selector: 'app-drawing',
  standalone: true,
  template: `
    <div
      class="preview-frame border-box round-1 fullwidth fullheight border-box"
      id="surface-parent"
      data-testid="drawing"
      [class.streaming]="state === DrawingState.Streaming"
      [class.error]="state === DrawingState.Error"
    >
      <canvas
        class="surface"
        data-testid="drawing-surface"
        id="canvas-surface"
        [class.hidden]="!scene?.drawing"
        [class.capturing]="mode === 'capture'"
        (mousedown)="onMouseDown($event)"
        (mousemove)="onMouseMove($event)"
        (mouseup)="onMouseUp($event)"
      ></canvas>
    </div>
  `,
  styleUrl: './drawing-surface.component.scss',
})
export class DrawingSurfaceComponent implements AfterViewInit, OnDestroy {
  DrawingState = DrawingState;

  private __drawing?: Drawing;
  surface?: Surface;
  scene?: Scene;
  controls?: Controls;

  get mode() {
    return this.controls?.mode || 'render';
  }
  @Input() set mode(newMode: SurfaceMode) {
    if (!this.controls) return;
    this.controls.mode = newMode;
  }

  @Input() state = DrawingState.Disabled;

  @Input() set drawing(d: RawDrawing | undefined) {
    this.setDrawing(d);
  }
  @Output() roi = new EventEmitter<BoxLike>();

  constructor(private elRef: ElementRef) {}

  ngOnDestroy(): void {
    this.mainLoop = () => {};
  }

  ngAfterViewInit(): void {
    const canvas = this.elRef.nativeElement.querySelector('#canvas-surface');
    const parent = this.elRef.nativeElement.querySelector('#surface-parent');
    this.surface = new Surface(canvas, parent);
    this.scene = new Scene(this.surface);
    this.controls = new Controls(this.surface, this.scene);
    this.mainLoop(this.state, this.__drawing, this.scene, this.controls);
  }

  mainLoop(
    state: DrawingState,
    drawing?: Drawing,
    scene?: Scene,
    controls?: Controls,
  ) {
    if (state === DrawingState.Streaming && drawing && scene && controls) {
      let drawThis = drawing;
      if (controls.roiBox) {
        const roiBox = <ROIBoxDrawingElement>{
          type: 'roiBox',
          box: controls.roiBox,
        };
        drawThis = <Drawing>{
          ...this.__drawing,
          elements: [...drawing.elements, roiBox],
        };
      }
      scene.render(drawThis);
    } else {
      this.reset();
    }
    requestAnimationFrame(() => {
      this.mainLoop(this.state, this.__drawing, this.scene, this.controls);
    });
  }

  reset() {
    if (!this.scene?.pristine) {
      this.scene?.clear();
    }
    this.mode = 'render';
  }

  async setDrawing(d: RawDrawing | undefined) {
    if (!this.surface) return;
    if (!d) {
      delete this.__drawing;
      return;
    }
    this.__drawing = await preprocessDrawing(d, this.surface.getDimensions());
  }

  onMouseDown(evt: MouseEvent) {
    this.controls?.mouseDown(evt);
  }
  onMouseMove(evt: MouseEvent) {
    this.controls?.mouseMove(evt);
  }
  onMouseUp(evt: MouseEvent) {
    if (
      !this.controls ||
      !this.scene ||
      !this.scene.drawing ||
      !this.controls.roiBox
    )
      return;
    this.controls.mouseUp(evt);
    const proportionalROI = this.controls.roiBox.vectMul(
      this.scene.drawing.boundary
        .size()
        .mul(1 / this.scene.drawing.scale)
        .invert(),
    );
    this.roi.emit(proportionalROI);
  }
}
