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

import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { DeviceVisualizerComponent } from '../device-visualizer/device-visualizer.component';

@Component({
  selector: 'app-roi-display',
  standalone: true,
  host: { class: 'stack' },
  imports: [CommonModule],
  styles: `
    .roi-box {
      overflow: hidden;
      border-radius: var(--standard-spacing);
      border: var(--standard-border) solid var(--color-gray-soft);

      .row {
        border: var(--standard-border) solid var(--color-gray-soft);
        border-top: 0;
        border-left: 0;
        border-right: 0;

        &:last-of-type {
          border: none;
        }
      }
    }
  `,
  template: `
    <div class="stack gap-0 roi-box text-14">
      <div class="row p-2 bg-edgeaipf-gray">
        <span class="w-6">Name</span>
        <span class="w-6">Value</span>
      </div>
      @let roi = visualizer.roiSet$ | async;
      @if (roi) {
        <div class="row p-2">
          <span class="w-6">Offset X</span>
          <span class="w-6">{{ roi.offset.x }}</span>
        </div>
        <div class="row p-2">
          <span class="w-6">Offset Y</span>
          <span class="w-6">{{ roi.offset.y }}</span>
        </div>
        <div class="row p-2">
          <span class="w-6">Width</span>
          <span class="w-6">{{ roi.size.x }}</span>
        </div>
        <div class="row p-2">
          <span class="w-6">Height</span>
          <span class="w-6">{{ roi.size.y }}</span>
        </div>
      }
    </div>
    <div class="row gap-2">
      <button
        class="weak-hub-btn button"
        [disabled]="visualizer.surfaceMode === 'capture'"
        (click)="visualizer.resetROI()"
      >
        Reset
      </button>
      <button
        class="weak-hub-btn button"
        [disabled]="visualizer.surfaceMode === 'capture'"
        (click)="visualizer.surfaceMode = 'capture'"
      >
        Set
      </button>
    </div>
  `,
})
export class RoiDisplayComponent {
  @Input() visualizer!: DeviceVisualizerComponent;
}
