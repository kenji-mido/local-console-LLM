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

import { Component, OnDestroy, Signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  TableVirtualScrollDataSource,
  TableVirtualScrollModule,
} from 'ng-table-virtual-scroll';
import { ScrollingModule } from '@angular/cdk/scrolling';
import { FormsModule } from '@angular/forms';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { CardComponent } from '@app/layout/components/card/card.component';
import { DeviceInfo } from '@app/layout/components/device-info/device-info.component';
import {
  DragDropModule,
  CdkDragMove,
  CdkDragEnd,
} from '@angular/cdk/drag-drop';
import { IconTextComponent } from '@app/core/file/icon-text/icon-text.component';
import { DevicePipesModule } from '@app/core/device/device.pipes';
import { DeviceStatus, DeviceV2, isLocalDevice } from '@app/core/device/device';
import { MatRadioButton, MatRadioGroup } from '@angular/material/radio';
import { DeviceService } from '@app/core/device/device.service';
import { toSignal } from '@angular/core/rxjs-interop';
import { CdkMenu, CdkMenuItem, CdkMenuTrigger } from '@angular/cdk/menu';
import { DialogService } from '@app/layout/dialogs/dialog.service';
import { UserPromptNameDialog } from './user-prompt-name/user-prompt-name.dialog';
import { TextInputComponent } from '@app/layout/components/text-input/text-input.component';
import { AIModelInfo } from '@app/layout/components/aimodel-info/aimodel-info.component';
import { NetworkInfo } from '@app/layout/components/network-info/network-info.component';

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
    CardComponent,
    TableVirtualScrollModule,
    MatTableModule,
    MatRadioGroup,
    MatRadioButton,
    ScrollingModule,
    FormsModule,
    MatProgressSpinnerModule,
    DragDropModule,
    IconTextComponent,
    DevicePipesModule,
    CdkMenuTrigger,
    CdkMenu,
    CdkMenuItem,
    TextInputComponent,
    DeviceInfo,
    AIModelInfo,
    NetworkInfo,
  ],
})
export class DeviceManagementScreen implements OnDestroy {
  DeviceStatus = DeviceStatus;
  Tab = Tab;

  theme = 'light';
  itemSize = 47;
  infoSize = 56;
  minInfoSize = this.infoSize;
  initialInfoSize = this.infoSize; // used to control drag movement

  displayedColumns: string[] = [
    'device_name',
    'status',
    'port',
    'appFw',
    'sensorFw',
    'selector',
  ];

  devices: Signal<DeviceV2[]>;
  dataSource: TableVirtualScrollDataSource<DeviceV2> =
    new TableVirtualScrollDataSource<DeviceV2>([]);
  selectedRowIndex: any;
  selectedDevice: DeviceV2 | null = null;
  selectedDeviceId: string | null = null;

  selectedSection: Tab = Tab.Device;

  intervalHandler?: any;

  constructor(
    private deviceService: DeviceService,
    private dialogs: DialogService,
  ) {
    this.devices = toSignal(this.deviceService.devices$, {
      initialValue: [] as DeviceV2[],
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

  async onDeviceSelected(device: DeviceV2) {
    this.selectedDeviceId = device.device_id;
    this.selectedDevice = device;
  }

  async onDelete(device: DeviceV2) {
    const result = await this.dialogs.prompt({
      message: `'${device.device_name}' will be removed from Local Console.  Existing image and metadata will not be removed.`,
      title: 'Are you sure you want to delete the device?',
      actionButtons: [{ id: 'delete', text: 'Delete', variant: 'primary' }],
      type: 'warning',
    });
    if (result?.id === 'delete') {
      if (isLocalDevice(device)) {
        if (this.selectedDeviceId === device.device_id) {
          this.selectedDevice = null;
          this.selectedDeviceId = null;
        }
        await this.deviceService.deleteDevice(device);
      } else console.error('Delete not implemented for Online device');
    }
  }

  onRename(device: DeviceV2) {
    const dialogRef = this.dialogs.open(UserPromptNameDialog, {
      title: 'Rename Device',
      actionButtons: [{ id: 'rename', text: 'Rename', variant: 'primary' }],
      type: 'warning',
    });
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
