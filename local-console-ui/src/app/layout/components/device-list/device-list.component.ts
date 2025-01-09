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

import { Component, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  TableVirtualScrollDataSource,
  TableVirtualScrollModule,
} from 'ng-table-virtual-scroll';
import { DeviceService } from '../../../core/device/device.service';
import { DeviceV2, isLocalDevice } from '../../../core/device/device';
import { TABLE_ROW_HEIGHT } from '../../constants';
import { ScrollingModule } from '@angular/cdk/scrolling';
import { FormsModule } from '@angular/forms';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { FeaturesService } from '@app/core/common/features.service';
import { MatButtonModule } from '@angular/material/button';
import { DialogService } from '@app/layout/dialogs/dialog.service';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { isSysModule } from '@app/core/module/module';
import { FirmwarePipesModule } from '@app/core/firmware/firmware.pipes';
import { DevicePipesModule } from '@app/core/device/device.pipes';

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
  ],
})
export class DeviceListComponent {
  isLoading = false;
  theme = 'light';
  tableRowHeight = TABLE_ROW_HEIGHT;
  displayedColumns: string[] = ['id', 'type', 'status', 'created_time'];
  devices: DeviceV2[] = [];
  dataSource: TableVirtualScrollDataSource<DeviceV2> =
    new TableVirtualScrollDataSource<DeviceV2>();
  emptyDataSource = new TableVirtualScrollDataSource([
    { id: 1 },
    { id: 2 },
    { id: 3 },
    { id: 4 },
  ]);
  get features() {
    return this.featuresService.getFeatures();
  }

  constructor(
    private deviceService: DeviceService,
    private featuresService: FeaturesService,
    private dialogs: DialogService,
  ) {
    if (this.features.device_list.local_devices) {
      this.displayedColumns = [
        'name',
        'port',
        'sensorfw',
        'appfw',
        'status',
        'remove',
      ];
    }

    deviceService.devices$
      .pipe(takeUntilDestroyed())
      .subscribe((devices) => this.onDevicesLoaded(devices));
  }

  private onDevicesLoaded(devices: DeviceV2[]) {
    this.devices = devices.filter(this.showDevice.bind(this));
    this.dataSource = new TableVirtualScrollDataSource(this.devices);
  }

  showDevice(device: DeviceV2) {
    // If device is local or V2, then show
    if (this.features.device_list.local_devices) return true;
    return device.modules?.some(isSysModule);
  }

  async deleteDevice(device: DeviceV2) {
    if (this.features.device_list.local_devices && isLocalDevice(device)) {
      const result = await this.dialogs.prompt({
        message: `Are you sure you want to delete device '${device.device_name}'?`,
        title: 'Delete device?',
        actionButtons: [{ id: 'delete', text: 'Delete', variant: 'primary' }],
        type: 'warning',
      });
      if (result?.id == 'delete') {
        this.isLoading = true;
        await this.deviceService.deleteDevice(device);
        this.isLoading = false;
      }
    }
  }
}
