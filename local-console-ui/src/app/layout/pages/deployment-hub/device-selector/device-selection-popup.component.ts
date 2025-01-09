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

import { CommonModule, formatDate } from '@angular/common';
import { Component, Inject, LOCALE_ID } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import {
  MatDialogRef,
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogTitle,
} from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { DeviceStatus, DeviceV2 } from '@app/core/device/device';
import { DevicePipesModule } from '@app/core/device/device.pipes';
import { DeviceService } from '@app/core/device/device.service';
import { IconTextComponent } from '@app/core/file/icon-text/icon-text.component';

@Component({
  selector: 'app-device-selection-popup',
  templateUrl: './device-selection-popup.component.html',
  styleUrls: ['./device-selection-popup.component.scss'],
  standalone: true,
  imports: [
    MatDialogTitle,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    CommonModule,
    FormsModule,
    IconTextComponent,
    DevicePipesModule,
  ],
})
export class DeviceSelectionPopupComponent {
  DeviceStatus = DeviceStatus;
  theme = 'light';
  refreshIcon = 'images/light/reload_icon.svg';
  refresh_datetime: string = '';
  selectedDevice: string = '';
  device: DeviceV2 | null = null;
  devices;

  constructor(
    public dialogRef: MatDialogRef<DeviceSelectionPopupComponent>,
    private deviceService: DeviceService,
    @Inject(MAT_DIALOG_DATA) public data: any,
    @Inject(LOCALE_ID) private locale: string,
  ) {
    this.devices = toSignal(this.deviceService.devices$, {
      initialValue: [] as DeviceV2[],
    });

    this.refresh();
    if (data.selectedDevice) {
      this.selectedDevice = data.selectedDevice;
    }
  }

  onDeviceSelected(device: DeviceV2) {
    this.device = device;
  }

  onCancel(): void {
    this.device =
      this.devices().find(
        (device) => device.device_name == this.selectedDevice,
      ) || null;
    this.dialogRef.close(this.device);
  }

  onSelect(): void {
    this.dialogRef.close(this.device);
  }

  async refresh() {
    await this.deviceService.loadDevices();
    if (this.data.selectedDevice) {
      this.device =
        this.devices().find(
          (device) => device.device_name == this.data.selectedDevice,
        ) || null;
    }

    this.refresh_datetime = formatDate(
      new Date(),
      'yy.MM.dd HH:mm:ss',
      this.locale,
    );
  }
}
