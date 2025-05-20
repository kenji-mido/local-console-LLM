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

import {
  CdkDragEnd,
  CdkDragMove,
  DragDropModule,
} from '@angular/cdk/drag-drop';
import { CdkMenu, CdkMenuItem, CdkMenuTrigger } from '@angular/cdk/menu';
import { ScrollingModule } from '@angular/cdk/scrolling';
import { CommonModule } from '@angular/common';
import { Component, OnDestroy, Signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { DeviceStatus, LocalDevice } from '@app/core/device/device';
import { DevicePipesModule } from '@app/core/device/device.pipes';
import { DeviceService } from '@app/core/device/device.service';
import { IconTextComponent } from '@app/core/file/icon-text/icon-text.component';
import { AIModelInfo } from '@app/layout/components/aimodel-info/aimodel-info.component';
import { DeviceInfo } from '@app/layout/components/device-info/device-info.component';
import { NetworkInfo } from '@app/layout/components/network-info/network-info.component';
import { DialogService } from '@app/layout/dialogs/dialog.service';
import { action } from '@app/layout/dialogs/user-prompt/action';
import {
  TableVirtualScrollDataSource,
  TableVirtualScrollModule,
} from 'ng-table-virtual-scroll';
import { DeviceStatusBadgeComponent } from '../../../core/device/device-status/device-status-badge.component';
import {
  UserPromptNameDialog,
  UserPromptNameDialogData,
} from './user-prompt-name/user-prompt-name.dialog';

export enum Tab {
  Device = 'Device',
  Network = 'Network',
  Model = 'Model',
}

@Component({
  selector: 'app-device-management',
  templateUrl: './device-management.screen.html',
  styleUrls: ['./device-management.screen.scss'],
  standalone: true,
  imports: [
    CommonModule,
    TableVirtualScrollModule,
    MatTableModule,
    ScrollingModule,
    FormsModule,
    MatProgressSpinnerModule,
    DragDropModule,
    IconTextComponent,
    DevicePipesModule,
    CdkMenuTrigger,
    CdkMenu,
    CdkMenuItem,
    DeviceInfo,
    AIModelInfo,
    NetworkInfo,
    DeviceStatusBadgeComponent,
  ],
})
export class DeviceManagementScreen implements OnDestroy {
  DeviceStatus = DeviceStatus;
  Tab = Tab;

  theme = 'light';
  itemSize = 47;
  infoSize = 0;
  minInfoSize = 56;
  initialInfoSize = this.infoSize; // used to control drag movement

  displayedColumns: string[] = [
    'device_name',
    'status',
    'port',
    'type',
    'appFw',
    'sensorFw',
    'selector',
  ];

  devices: Signal<LocalDevice[]>;
  dataSource: TableVirtualScrollDataSource<LocalDevice> =
    new TableVirtualScrollDataSource<LocalDevice>([]);
  selectedRowIndex: any;
  selectedDevice: LocalDevice | null = null;
  selectedDeviceId: string | null = null;

  selectedSection: Tab = Tab.Device;

  intervalHandler?: any;

  constructor(
    private deviceService: DeviceService,
    private dialogs: DialogService,
  ) {
    this.devices = toSignal(this.deviceService.devices$, {
      initialValue: [] as LocalDevice[],
    });

    this.deviceService.loadDevices();
    this.intervalHandler = setInterval(
      () => this.deviceService.loadDevices(),
      1000,
    );

    this.deviceService.devices$.subscribe((data) => {
      /**
       * FIXME: Hover events are triggered although mouse is outside div.
       * https://stackoverflow.com/questions/46923371/mouseenter-continues-to-run-even-with-the-mouse-being-outside-the-div
       *
       * HACK: Avoid update by comparing data
       */
      if (JSON.stringify(this.dataSource.data) !== JSON.stringify(data)) {
        this.dataSource.data = data;
        // update selected device information
        this.selectedDevice =
          data.find((device) => device.device_id === this.selectedDeviceId) ||
          null;
        this.selectedDeviceId = this.selectedDevice?.device_id || null;
      }
    });

    document.addEventListener('DOMContentLoaded', () => {
      const deviceDetailsHeader = document.getElementById(
        'device_details_header_id',
      );
      if (deviceDetailsHeader) {
        this.minInfoSize = parseInt(
          window
            .getComputedStyle(deviceDetailsHeader, null)
            .getPropertyValue('min-height'),
        );
      }
    });
  }

  onDragMoved(event: CdkDragMove): void {
    this.infoSize = Math.max(
      this.initialInfoSize - event.distance.y,
      this.minInfoSize,
    );
    event.source.setFreeDragPosition({ x: 0, y: 0 });
  }

  onDragEnded(event: CdkDragEnd): void {
    this.initialInfoSize = this.infoSize;
  }

  selectDevice() {
    this.selectedSection = Tab.Device;
  }

  selectNetwork() {
    this.selectedSection = Tab.Network;
  }

  selectModel() {
    this.selectedSection = Tab.Model;
  }

  async onDeviceSelected(device: LocalDevice) {
    this.selectedDeviceId = device.device_id;
    this.selectedDevice = device;
    if (this.infoSize === 0) {
      this.infoSize = 0.33 * window.innerHeight;
    }
    this.initialInfoSize = this.infoSize;
  }

  async onDelete(device: LocalDevice) {
    const result = await this.dialogs.prompt({
      message: `'${device.device_name}' will be removed from Local Console.  Existing image and metadata will not be removed.`,
      title: 'Are you sure you want to delete the device?',
      actionButtons: [action.negative('delete', 'Delete')],
      type: 'warning',
      showCancelButton: true,
    });
    if (result?.id === 'delete') {
      if (this.selectedDeviceId === device.device_id) {
        this.selectedDevice = null;
        this.selectedDeviceId = null;
      }
      await this.deviceService.deleteDevice(device);
    }
  }

  onRename(device: LocalDevice) {
    let data: UserPromptNameDialogData = {
      title: 'Rename Device',
      message: '',
      actionButtons: [action.normal('rename', 'Rename')],
      type: 'warning',
      deviceName: device.device_name,
      showCancelButton: true,
    };

    const dialogRef = this.dialogs.open(UserPromptNameDialog, data);
    dialogRef.closed.subscribe(async (result) => {
      if (typeof result !== 'string') return;
      await this.deviceService.updateDeviceName(device.device_id, result);
      console.debug(`Rename from ${device.device_name} to ${result}`);
    });
  }

  ngOnDestroy() {
    if (this.intervalHandler) {
      clearInterval(this.intervalHandler);
      this.intervalHandler = undefined;
    }
  }
}
