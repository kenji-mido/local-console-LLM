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

import { NgModule, Pipe, PipeTransform } from '@angular/core';
import {
  DeviceStatus,
  deviceTypeToArchetype,
  LocalDevice,
} from '@app/core/device/device';

@Pipe({
  name: 'deviceStatusSvg',
  standalone: true,
})
export class DeviceStatusSvgPipe implements PipeTransform {
  transform(
    connectionState: string | undefined,
    theme: string = 'light',
  ): string {
    switch (connectionState) {
      case DeviceStatus.Connected:
      case DeviceStatus.Connecting:
        return `images/${theme}/device_status_connected.svg`;
      case DeviceStatus.Periodic:
        return `images/${theme}/device_status_periodic.svg`;
      case DeviceStatus.Disconnected:
      default:
        return `images/${theme}/device_status_disconnected.svg`;
    }
  }
}

@Pipe({
  name: 'archetype',
  standalone: true,
})
export class DeviceArchetypePipe implements PipeTransform {
  transform(device?: LocalDevice) {
    return deviceTypeToArchetype(device?.device_type);
  }
}

@NgModule({
  imports: [DeviceStatusSvgPipe, DeviceArchetypePipe],
  exports: [DeviceStatusSvgPipe, DeviceArchetypePipe],
})
export class DevicePipesModule {}
