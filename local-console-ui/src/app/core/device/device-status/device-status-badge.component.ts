/**
 * Copyright 2025 Sony Semiconductor Solutions Corp.
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

import { Component, Input } from '@angular/core';
import { DeviceStatus } from '../device';
import { DevicePipesModule } from '../device.pipes';

@Component({
  selector: 'app-device-status-badge',
  standalone: true,
  imports: [DevicePipesModule],
  template: `
    <div
      class="row gap-1 align-center"
      [class.blinking]="__deviceStatus === 'Connecting'"
    >
      <img [src]="__deviceStatus | deviceStatusSvg" />
      <span data-testid="text">{{ __deviceStatus }}</span>
    </div>
  `,
})
export class DeviceStatusBadgeComponent {
  __deviceStatus = DeviceStatus.Disconnected;
  @Input() set deviceStatus(status: DeviceStatus | undefined) {
    this.__deviceStatus = status || DeviceStatus.Disconnected;
  }
}
