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

import { Point } from 'electron';

export interface DrawingElement {
  type: 'box' | 'label' | 'image' | 'nativeImage' | 'roiBox';
}

export interface ImageDrawingElement extends DrawingElement {
  type: 'image';
  data: string;
}
export interface NativeImageDrawingElement extends DrawingElement {
  type: 'nativeImage';
  img: HTMLImageElement;
  offset: Point2D;
  size: Point2D;
}
export interface BoxDrawingElement extends DrawingElement, BoxLike {
  type: 'box';
  color: string;
  width: number;
  min: Point2D;
  max: Point2D;
}
export interface LabelDrawingElement extends DrawingElement {
  type: 'label';
  text: string;
  bgColor: string;
  txtColor: string;
  fixed: boolean;
  // Bottom-left corner
  position: Point2D;
}
export interface ROIBoxDrawingElement extends DrawingElement {
  type: 'roiBox';
  box: BoxLike;
}
export class Point2D {
  constructor(
    public x: number,
    public y: number,
  ) {}

  add(x: number, y: number): Point2D;
  add(p: Point2D): Point2D;
  add(x: number | Point2D, y?: number): Point2D {
    if (x instanceof Point2D) {
      y = x.y;
      x = x.x;
    }
    return new Point2D(this.x + x, this.y + y!);
  }

  mul(scalar: number) {
    return new Point2D(this.x * scalar, this.y * scalar);
  }

  clone() {
    return new Point2D(this.x, this.y);
  }

  invert() {
    return new Point2D(1 / this.x, 1 / this.y);
  }

  vectMul(v: Point2D) {
    return new Point2D(this.x * v.x, this.y * v.y);
  }

  round() {
    return new Point2D(Math.round(this.x), Math.round(this.y));
  }
}

export interface BoxLike {
  min: Point2D;
  max: Point2D;
}

export class Box implements BoxLike {
  public min: Point2D;
  public max: Point2D;

  constructor(box: BoxLike);
  constructor(min: Point2D, max: Point2D);
  constructor(x1: number, y1: number, x2: number, y2: number);
  constructor(
    arg1: BoxLike | Point2D | number,
    arg2?: Point2D | number,
    arg3?: number,
    arg4?: number,
  ) {
    if (
      typeof arg1 === 'number' &&
      typeof arg2 === 'number' &&
      typeof arg3 === 'number' &&
      typeof arg4 === 'number'
    ) {
      // Handle the case with four coordinates
      this.min = new Point2D(arg1, arg2);
      this.max = new Point2D(arg3, arg4);
    } else if (arg1 instanceof Point2D && arg2 instanceof Point2D) {
      // Handle the case with two Point2D objects
      this.min = arg1;
      this.max = arg2;
    } else if (
      Object.hasOwn(<object>arg1, 'min') &&
      Object.hasOwn(<object>arg1, 'max')
    ) {
      const b = <BoxLike>arg1;
      this.min = b.min.clone();
      this.max = b.max.clone();
    } else {
      throw new Error('Invalid constructor arguments');
    }
    this.sortBox();
  }

  sortBox() {
    const min = this.min;
    const max = this.max;
    this.min = new Point2D(Math.min(min.x, max.x), Math.min(min.y, max.y));
    this.max = new Point2D(Math.max(min.x, max.x), Math.max(min.y, max.y));
  }

  isPointInside(p: Point2D) {
    return (
      p.x >= this.min.x &&
      p.y >= this.min.y &&
      p.x <= this.max.x &&
      p.y <= this.max.y
    );
  }

  clamp(box: Box) {
    const min = new Point2D(
      Math.max(this.min.x, box.min.x),
      Math.max(this.min.y, box.min.y),
    );
    const max = new Point2D(
      Math.min(this.max.x, box.max.x),
      Math.min(this.max.y, box.max.y),
    );
    return new Box(min, max);
  }

  mul(scalar: number) {
    return new Box(this.min.mul(scalar), this.max.mul(scalar));
  }

  vectMul(v: Point2D) {
    return new Box(this.min.vectMul(v), this.max.vectMul(v));
  }

  add(v: Point2D) {
    return new Box(this.min.add(v), this.max.add(v));
  }

  size() {
    return this.max.add(this.min.mul(-1));
  }
}

export interface RawDrawing {
  elements: DrawingElement[];
}

export interface Drawing {
  elements: DrawingElement[];
  boundary: Box;
  scale: number;
}
