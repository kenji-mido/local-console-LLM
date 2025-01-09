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

import { ROI_COLOR, ROI_WIDTH, Scene } from './scene';
import { Surface } from './surface';
import { Drawing, Point2D } from './drawing';
import { Drawings } from '@samplers/drawing';

class MockContext {
  clearRect = jest.fn();
  drawImage = jest.fn();
  fillText = jest.fn();
  fillRect = jest.fn();
  beginPath = jest.fn();
  rect = jest.fn();
  stroke = jest.fn();
  set strokeStyle(s: any) {}
  set lineWidth(l: any) {}
}

class MockCanvas {
  clientWidth = 800;
  clientHeight = 600;
  getContext = jest.fn();

  constructor(private mockCtx: MockContext) {
    this.getContext.mockReturnValue(this.mockCtx);
  }
}

class MockSurface {
  constructor(
    public ctx: MockContext,
    public canvas: MockCanvas,
  ) {}
}

describe('Scene', () => {
  let surface: MockSurface;
  let scene: Scene;
  let drawing: Drawing;

  beforeEach(() => {
    // Mock canvas and its context
    const mockCtx = new MockContext();
    const mockCanvas = new MockCanvas(mockCtx);
    surface = new MockSurface(mockCtx, mockCanvas);
    scene = new Scene(surface as unknown as Surface);

    // Setup a mock drawing
    drawing = Drawings.sample();
  });

  test('clear should clear the canvas', () => {
    scene.clear();
    expect(surface.ctx.clearRect).toHaveBeenCalledWith(0, 0, 800, 600);
  });

  test('render should set current drawing and call draw methods', () => {
    scene.render(drawing);
    expect(scene.drawing).toBe(drawing);
    expect(surface.ctx.clearRect).toHaveBeenCalled(); // Canvas was cleared before drawing
    expect(surface.ctx.drawImage).toHaveBeenCalled(); // Image was drawn
    expect(surface.ctx.fillText).toHaveBeenCalled(); // Label was drawn
    expect(surface.ctx.rect).toHaveBeenCalledTimes(6); // Box and ROI box with corners were drawn
  });

  test('label should not render if no text provided', () => {
    const label = Drawings.sampleLabel();
    label.text = '';

    scene.render({
      ...drawing,
      elements: [label],
    });

    expect(surface.ctx.fillRect).not.toHaveBeenCalled();
    expect(surface.ctx.fillText).not.toHaveBeenCalled();
  });

  test('roi should render five boxes', () => {
    const roi = Drawings.sampleRoi();
    const strokeStyleSetter = jest.spyOn(surface.ctx, 'strokeStyle', 'set');
    const lineWidthSetter = jest.spyOn(surface.ctx, 'lineWidth', 'set');
    scene.render({
      ...drawing,
      elements: [roi],
    });

    const fiveCalls = [0, 0, 0, 0, 0];
    expect(strokeStyleSetter.mock.calls).toEqual(
      fiveCalls.map((i) => [ROI_COLOR]),
    );
    expect(lineWidthSetter.mock.calls).toEqual(
      fiveCalls.map((i) => [ROI_WIDTH]),
    );
    expect(surface.ctx.rect).toHaveBeenCalledTimes(5);
  });
});
