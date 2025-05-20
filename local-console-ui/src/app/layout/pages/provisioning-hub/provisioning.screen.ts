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
import { Component, Inject, LOCALE_ID, ViewChild } from '@angular/core';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { DeviceService } from '@app/core/device/device.service';
import { TextInputComponent } from '@app/layout/components/text-input/text-input.component';
import { firstValueFrom } from 'rxjs';
import { LocalDevice } from '../../../core/device/device';
import { DeviceDetailsComponent } from '../../../core/device/device-details/device-details.component';
import { InfotipDirective } from '../../../core/feedback/infotip.component';
import { SegmentsComponent } from '../../../core/option/segments.component';
import { NetworkSettingsPane } from './network-settings/network-settings.pane';

type HubMode = 'Register' | 'Connect';

@Component({
  selector: 'app-provisioning',
  templateUrl: './provisioning.screen.html',
  styleUrls: ['./provisioning.screen.scss'],
  standalone: true,
  imports: [
    NetworkSettingsPane,
    CommonModule,
    DeviceDetailsComponent,
    TextInputComponent,
    FormsModule,
    ReactiveFormsModule,
    MatProgressSpinnerModule,
    InfotipDirective,
    SegmentsComponent,
    MatSelectModule,
  ],
})
export class ProvisioningScreen {
  theme = 'light';
  isLoading = false;
  qrCode!: string;
  qrCreatedDate?: Date;
  qrExpiredDate?: Date;
  createDeviceGroup = new FormGroup({
    device_name: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required],
    }),
    mqtt_port: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required],
    }),
  });
  private __hubMode: HubMode = 'Register';
  get hubMode() {
    return this.__hubMode;
  }
  set hubMode(mode: HubMode) {
    this.__hubMode = mode;
    if (mode === 'Connect') this.deviceService.loadDevices();
  }
  selectedDevice?: LocalDevice;
  intervalHandler?: number;

  @ViewChild(NetworkSettingsPane) networkSettings!: NetworkSettingsPane;

  constructor(
    protected deviceService: DeviceService,
    @Inject(LOCALE_ID) private locale: string,
  ) {
    this.deviceService.loadDevices();
    this.intervalHandler = window.setInterval(
      () => this.deviceService.loadDevices(),
      3000,
    );

    this.deviceService.devices$.subscribe((devices) => {
      if (this.selectedDevice !== undefined) {
        const current_port = this.selectedDevice.device_id;
        this.selectedDevice = devices.filter(
          (device) => device.device_id === current_port,
        )[0];
      } else {
        this.selectedDevice = devices[0];
      }
    });
  }

  onGenerateQrCode(event: {
    qrCode: string;
    qrCreatedDate: Date;
    qrExpiredDate: Date;
  }) {
    this.qrCode = event.qrCode;
    this.qrCreatedDate = event.qrCreatedDate;
    this.qrExpiredDate = event.qrExpiredDate;
  }
  async refresh() {
    this.isLoading = true;
    await this.deviceService.loadDevices();
    this.isLoading = false;
  }

  clearDeviceCreation() {
    this.createDeviceGroup.reset();
  }

  async createDevice() {
    if (this.createDeviceGroup.valid) {
      const device_name = this.createDeviceGroup.value.device_name;
      const mqtt_port = this.createDeviceGroup.value.mqtt_port;
      if (device_name && mqtt_port) {
        const intPort = Number.parseInt(mqtt_port);
        this.isLoading = true;
        const result: {} | null = await this.deviceService.createDevice(
          device_name,
          intPort,
        );
        if (result !== null) {
          this.selectedDevice = (
            await firstValueFrom(this.deviceService.devices$)
          ).find((d) => d.device_id === intPort.toString());
          this.hubMode = 'Connect';
        }
        this.isLoading = false;
      } else {
        console.log('Values are invalid');
      }
    }
  }

  private stopInterval() {
    if (this.intervalHandler) {
      clearInterval(this.intervalHandler);
      this.intervalHandler = undefined;
    }
  }

  ngOnDestroy() {
    this.stopInterval();
  }

  protected readonly Number = Number;
}
