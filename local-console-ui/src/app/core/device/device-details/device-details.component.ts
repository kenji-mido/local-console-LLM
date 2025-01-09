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

import { Component, Input, OnDestroy } from '@angular/core';
import { DeviceFrame, LocalDevice } from '../device';
import { DeviceService } from '../device.service';
import { CommonModule } from '@angular/common';
import { DialogService } from '@app/layout/dialogs/dialog.service';
import { CardComponent } from '@app/layout/components/card/card.component';
import { DevicePipesModule } from '../device.pipes';
import { DrawingSurfaceComponent } from '../../drawing/drawing-surface.component';
import { DeviceVisualizerComponent } from '../device-visualizer/device-visualizer.component';

@Component({
  selector: 'app-device-details',
  standalone: true,
  imports: [
    CommonModule,
    CardComponent,
    DevicePipesModule,
    DrawingSurfaceComponent,
    DeviceVisualizerComponent,
  ],
  templateUrl: './device-details.component.html',
  styleUrl: './device-details.component.scss',
})
export class DeviceDetailsComponent {
  @Input() selectedDevice?: LocalDevice;
}
