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
import { Component, Input, SimpleChanges } from '@angular/core';
import { CardComponent } from '../card/card.component';
import { DeviceV2 } from '@app/core/device/device';
import { SysAppModuleStateV2, isSysModuleState } from '@app/core/module/sysapp';

interface DeviceInfoTabItems {
  sensor: string | undefined;
  main_chip: string | undefined;
  sensor_chip_fw_main: string | undefined;
  sensor_chip_fw_loader: string | undefined;
  processing_state: string | undefined;
  device_id: string | undefined;
  internal_id: string | undefined;
}

@Component({
  selector: 'app-device-info',
  templateUrl: './device-info.component.html',
  styleUrls: ['./device-info.component.scss'],
  standalone: true,
  imports: [CommonModule, CardComponent],
})
export class DeviceInfo {
  device_info: DeviceInfoTabItems = {
    sensor: undefined,
    main_chip: undefined,
    sensor_chip_fw_main: undefined,
    sensor_chip_fw_loader: undefined,
    processing_state: undefined,
    device_id: undefined,
    internal_id: undefined,
  };

  @Input() device: DeviceV2 | null = null;

  ngOnChanges(changes: SimpleChanges) {
    this.onDeviceInfoReceived(changes['device'].currentValue);
  }
  onDeviceInfoReceived(device: DeviceV2 | null) {
    this.device = device;
    if (
      device === null ||
      device.modules === null ||
      !isSysModuleState(device.modules?.[0].property.state!)
    ) {
      this.device_info = {
        sensor: undefined,
        main_chip: undefined,
        sensor_chip_fw_main: undefined,
        sensor_chip_fw_loader: undefined,
        processing_state: undefined,
        device_id: undefined,
        internal_id: undefined,
      };
      return;
    }
    const device_state: SysAppModuleStateV2 =
      device.modules?.[0].property.state!;
    this.device_info = {
      sensor: device_state.device_info?.sensors?.[0].name,
      main_chip: device_state.device_info?.processors?.[0].firmware_version,
      sensor_chip_fw_main:
        device_state.device_info?.sensors?.[0].firmware_version,
      sensor_chip_fw_loader:
        device_state.device_info?.sensors?.[0].loader_version,
      processing_state: device_state.device_state?.process_state,
      device_id: device.device_id,
      internal_id: device.internal_device_id,
    };
  }
}
