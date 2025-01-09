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

import { Pipe, PipeTransform, NgModule } from '@angular/core';
import { DeviceStatus, DeviceV2, isLocalDevice } from '@app/core/device/device';

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
        return `images/${theme}/device_status_connected.svg`;
      case DeviceStatus.Disconnected:
        return `images/${theme}/device_status_disconnected.svg`;
      default:
        return `images/${theme}/device_status_unknown.svg`;
    }
  }
}

@Pipe({
  name: 'localDevices',
  standalone: true,
})
export class DeviceListLocalFilterPipe implements PipeTransform {
  transform(value: DeviceV2[] | null | undefined) {
    value ||= [];
    return value.filter(isLocalDevice);
  }
}

@NgModule({
  imports: [DeviceStatusSvgPipe, DeviceListLocalFilterPipe],
  exports: [DeviceStatusSvgPipe, DeviceListLocalFilterPipe],
})
export class DevicePipesModule {}
