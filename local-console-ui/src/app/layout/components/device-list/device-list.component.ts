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

import { ScrollingModule } from '@angular/cdk/scrolling';
import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { DevicePipesModule } from '@app/core/device/device.pipes';
import { FirmwarePipesModule } from '@app/core/firmware/firmware.pipes';
import { DialogService } from '@app/layout/dialogs/dialog.service';
import { action } from '@app/layout/dialogs/user-prompt/action';
import {
  TableVirtualScrollDataSource,
  TableVirtualScrollModule,
} from 'ng-table-virtual-scroll';
import { LocalDevice } from '../../../core/device/device';
import { DeviceStatusBadgeComponent } from '../../../core/device/device-status/device-status-badge.component';
import { DeviceService } from '../../../core/device/device.service';
import { TABLE_ROW_HEIGHT } from '../../constants';

@Component({
  selector: 'app-device-list',
  templateUrl: './device-list.component.html',
  styleUrls: ['./device-list.component.scss'],
  standalone: true,
  imports: [
    DevicePipesModule,
    ScrollingModule,
    TableVirtualScrollModule,
    FormsModule,
    MatProgressSpinnerModule,
    CommonModule,
    MatTableModule,
    MatButtonModule,
    FirmwarePipesModule,
    DeviceStatusBadgeComponent,
  ],
})
export class DeviceListComponent {
  isLoading = false;
  theme = 'light';
  tableRowHeight = TABLE_ROW_HEIGHT;
  displayedColumns: string[] = ['id', 'type', 'status', 'created_time'];
  devices: LocalDevice[] = [];
  dataSource: TableVirtualScrollDataSource<LocalDevice> =
    new TableVirtualScrollDataSource<LocalDevice>();
  emptyDataSource = new TableVirtualScrollDataSource([
    { id: 1 },
    { id: 2 },
    { id: 3 },
    { id: 4 },
  ]);

  constructor(
    private deviceService: DeviceService,
    private dialogs: DialogService,
  ) {
    this.displayedColumns = [
      'name',
      'port',
      'sensorfw',
      'appfw',
      'status',
      'remove',
    ];

    deviceService.devices$.pipe(takeUntilDestroyed()).subscribe((devices) => {
      this.devices = devices;
      this.dataSource = new TableVirtualScrollDataSource(this.devices);
    });
  }

  async deleteDevice(device: LocalDevice) {
    const result = await this.dialogs.prompt({
      message: `Are you sure you want to delete device '${device.device_name}'?`,
      title: 'Delete device?',
      actionButtons: [action.negative('delete', 'Delete')],
      type: 'warning',
      showCancelButton: true,
    });
    if (result?.id == 'delete') {
      this.isLoading = true;
      await this.deviceService.deleteDevice(device);
      this.isLoading = false;
    }
  }
}
