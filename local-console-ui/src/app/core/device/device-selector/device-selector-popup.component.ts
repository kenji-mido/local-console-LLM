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

import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { CommonModule } from '@angular/common';
import { Component, effect, Inject, LOCALE_ID, Signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { LcDateTimePipe } from '@app/core/common/date';
import {
  DeviceStatus,
  getSystemModule,
  LocalDevice,
} from '@app/core/device/device';
import { DevicePipesModule } from '@app/core/device/device.pipes';
import { DeviceService } from '@app/core/device/device.service';
import { DeviceStatusBadgeComponent } from '../device-status/device-status-badge.component';

export interface DeviceSelectionPopupData {
  selectedDevice?: LocalDevice;
}

@Component({
  selector: 'app-device-selector-popup',
  templateUrl: './device-selector-popup.component.html',
  styleUrls: ['./device-selector-popup.component.scss'],
  standalone: true,
  imports: [
    MatButtonModule,
    MatIconModule,
    CommonModule,
    FormsModule,
    DevicePipesModule,
    LcDateTimePipe,
    DeviceStatusBadgeComponent,
  ],
})
export class DeviceSelectionPopupComponent {
  DeviceStatus = DeviceStatus;
  theme = 'light';
  refreshIcon = 'images/light/reload_icon.svg';
  refresh_datetime = new Date();
  selectedDevice?: LocalDevice;
  devices: Signal<LocalDevice[]>;
  getSystemModule = getSystemModule;

  constructor(
    public dialogRef: DialogRef<LocalDevice | null>,
    private deviceService: DeviceService,
    @Inject(DIALOG_DATA) public data: DeviceSelectionPopupData,
    @Inject(LOCALE_ID) private locale: string,
  ) {
    this.devices = toSignal(this.deviceService.devices$, {
      initialValue: [] as LocalDevice[],
    });

    effect(() => {
      if (this.selectedDevice) {
        this.selectedDevice = this.devices().find(
          (device) => device.device_name == this.selectedDevice?.device_name,
        );
      }
    });

    this.refresh();
    this.selectedDevice = data.selectedDevice;
  }

  onDeviceSelected(device: LocalDevice) {
    this.selectedDevice = device;
  }

  onCancel(): void {
    this.dialogRef.close(
      this.devices().find(
        (device) => device.device_name == this.data.selectedDevice?.device_name,
      ) || null,
    );
  }

  onSelect(): void {
    this.dialogRef.close(this.selectedDevice || null);
  }

  async refresh() {
    await this.deviceService.loadDevices();
    this.refresh_datetime = new Date();
  }
}
