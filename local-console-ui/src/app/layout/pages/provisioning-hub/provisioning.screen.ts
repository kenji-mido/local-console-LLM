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

import { Component, Inject, LOCALE_ID, ViewChild } from '@angular/core';
import { NetworkSettingsPane } from './network-settings/network-settings.pane';
import { isLocalDevice, LocalDevice } from '../../../core/device/device';
import { CardComponent } from '../../components/card/card.component';
import { FeaturesService } from '@app/core/common/features.service';
import { CommonModule, formatDate } from '@angular/common';
import { DeviceDetailsComponent } from '../../../core/device/device-details/device-details.component';
import { DeviceListComponent } from '@app/layout/components/device-list/device-list.component';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { TextInputComponent } from '@app/layout/components/text-input/text-input.component';
import { DeviceService } from '@app/core/device/device.service';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { firstValueFrom } from 'rxjs';
import { InfotipDirective } from '../../../core/feedback/infotip.component';
import { SegmentsComponent } from '../../../core/option/segments.component';
import { MatSelectModule } from '@angular/material/select';
import { DevicePipesModule } from '@app/core/device/device.pipes';

type HubMode = 'Register' | 'Connect';

@Component({
  selector: 'app-provisioning',
  templateUrl: './provisioning.screen.html',
  styleUrls: ['./provisioning.screen.scss'],
  standalone: true,
  imports: [
    NetworkSettingsPane,
    CardComponent,
    DeviceListComponent,
    CommonModule,
    DeviceDetailsComponent,
    TextInputComponent,
    FormsModule,
    ReactiveFormsModule,
    MatProgressSpinnerModule,
    InfotipDirective,
    SegmentsComponent,
    MatSelectModule,
    DevicePipesModule,
  ],
})
export class ProvisioningScreen {
  theme = 'light';
  isLoading = false;
  refresh_datetime: string = '';
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

  get features() {
    return this.featuresService.getFeatures();
  }

  constructor(
    private featuresService: FeaturesService,
    protected deviceService: DeviceService,
    @Inject(LOCALE_ID) private locale: string,
  ) {
    this.deviceService.loadDevices();
    firstValueFrom(this.deviceService.devices$).then((device) => {
      this.selectedDevice = device.filter(isLocalDevice)[0];
    });
    this.intervalHandler = window.setInterval(
      () => this.deviceService.loadDevices(),
      3000,
    );

    this.deviceService.devices$.subscribe(() => {
      if (this.selectedDevice !== undefined) {
        const current_port = this.selectedDevice.port;
        firstValueFrom(this.deviceService.devices$).then((device) => {
          this.selectedDevice = device
            .filter(isLocalDevice)
            .filter((device) => device.port === current_port)[0];
        });
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
    this.refresh_datetime = formatDate(
      new Date(),
      'yy.MM.dd HH:mm',
      this.locale,
    );
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
          )
            .filter(isLocalDevice)
            .find((d) => d.port === intPort);
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
}
