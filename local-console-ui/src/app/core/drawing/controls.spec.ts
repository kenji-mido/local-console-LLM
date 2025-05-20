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

import { Controls } from './controls';
import { Box, Point2D } from './drawing';
import { Scene } from './scene';
import { Surface } from './surface';

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
  getOffset = jest.fn();
}

class MockScene {
  drawing = {
    boundary: new Box(new Point2D(0, 0), new Point2D(1000, 1000)),
    scale: 1,
  };
}

describe('Controls', () => {
  let controls: Controls;
  let surface: MockSurface;
  let scene: Scene;
  let mockEvent: MouseEvent;

  beforeEach(() => {
    const mockCtx = new MockContext();
    const mockCanvas = new MockCanvas(mockCtx);
    surface = new MockSurface(mockCtx, mockCanvas);
    scene = new MockScene() as unknown as Scene;
    controls = new Controls(surface as unknown as Surface, scene);
    mockEvent = { clientX: 100, clientY: 150 } as MouseEvent;
  });

  describe('mode setter', () => {
    it('should reset roiBox when changing mode', () => {
      controls.roiBox = new Box(new Point2D(0, 0), new Point2D(1, 1));
      controls.mode = 'capture';
      expect(controls.roiBox).toBeUndefined();
    });
  });

  describe('roi box correctly created', () => {
    it('should set roibox to correct dimensions', () => {
      controls.mode = 'capture';
      surface.getOffset.mockReturnValue(new Point2D(0, 0));
      controls.mouseDown({ clientX: 100, clientY: 150 } as MouseEvent);
      controls.mouseMove({ clientX: 200, clientY: 300 } as MouseEvent);
      expect(controls.roiBox?.min).toEqual(new Point2D(100, 150));
      expect(controls.roiBox?.max).toEqual(new Point2D(200, 300));
    });

    it('should set roibox to correct dimensions even if backwards', () => {
      controls.mode = 'capture';
      surface.getOffset.mockReturnValue(new Point2D(0, 0));
      controls.mouseDown({ clientX: 200, clientY: 150 } as MouseEvent);
      controls.mouseMove({ clientX: 100, clientY: 300 } as MouseEvent);
      expect(controls.roiBox?.min).toEqual(new Point2D(100, 150));
      expect(controls.roiBox?.max).toEqual(new Point2D(200, 300));
    });

    it('should not set roibox when render', () => {
      controls.mode = 'render';
      controls.mouseDown({ clientX: 100, clientY: 150 } as MouseEvent);
      controls.mouseMove({ clientX: 200, clientY: 300 } as MouseEvent);
      expect(controls.roiBox).toBeFalsy();
    });

    it('should set roibox to correct dimensions when offset is not nil', () => {
      controls.mode = 'capture';
      surface.getOffset.mockReturnValue(new Point2D(100, 200));
      controls.mouseDown({ clientX: 280, clientY: 350 } as MouseEvent);
      controls.mouseMove({ clientX: 150, clientY: 300 } as MouseEvent);
      expect(controls.roiBox?.min).toEqual(new Point2D(50, 100));
      expect(controls.roiBox?.max).toEqual(new Point2D(180, 150));
    });

    it('should not set roibox if capture point is outside bounds', () => {
      controls.mode = 'capture';
      surface.getOffset.mockReturnValue(new Point2D(100, 200));
      scene.drawing!.boundary = new Box(
        new Point2D(0, 0),
        new Point2D(200, 130),
      );
      controls.mouseDown({ clientX: 280, clientY: 350 } as MouseEvent);
      controls.mouseMove({ clientX: 150, clientY: 300 } as MouseEvent);
      expect(controls.roiBox).toBeFalsy();
    });

    it('should not clamp roi if mouse moves outside bounds', () => {
      controls.mode = 'capture';
      surface.getOffset.mockReturnValue(new Point2D(100, 200));
      scene.drawing!.boundary = new Box(
        new Point2D(0, 0),
        new Point2D(200, 130),
      );
      controls.mouseDown({ clientX: 280, clientY: 300 } as MouseEvent);
      controls.mouseMove({ clientX: 150, clientY: 350 } as MouseEvent);
      expect(controls.roiBox?.min).toEqual(new Point2D(50, 100));
      expect(controls.roiBox?.max).toEqual(new Point2D(180, 130));
    });
  });
});
