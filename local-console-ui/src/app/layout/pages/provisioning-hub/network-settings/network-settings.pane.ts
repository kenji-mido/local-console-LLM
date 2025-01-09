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

import { Component, Output, EventEmitter, Input } from '@angular/core';
import { FormGroup, FormControl } from '@angular/forms';
import { RadioButtonComponent } from '../../../components/radio-button/radio-button.component';
import { ipAddressValidator } from '../../../../core/common/validation';
import { ROUTER_LINKS } from '../../../../core/config/routes';
import { CardComponent } from '../../../components/card/card.component';
import { CommonModule } from '@angular/common';
import { TextInputComponent } from '../../../components/text-input/text-input.component';
import { ReactiveFormsModule } from '@angular/forms';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ToggleComponent } from '../../../components/toggle/toggle.component';
import { QrService } from '../../../../core/qr/qr.service';
import { QrcodeComponent } from '../../../../core/qr/qrcode.component';
import { FeaturesService } from '../../../../core/common/features.service';
import { InfotipDirective } from '@app/core/feedback/infotip.component';

type InputType = 'text' | 'number' | 'email' | 'password';
export interface FormItems {
  name: string;
  label: string;
  required?: boolean;
  type?: InputType;
  maxLength: string;
  placeholder?: string;
}

@Component({
  selector: 'app-network-settings',
  templateUrl: './network-settings.pane.html',
  styleUrls: ['./network-settings.pane.scss'],
  standalone: true,
  imports: [
    CommonModule,
    CardComponent,
    TextInputComponent,
    RadioButtonComponent,
    ReactiveFormsModule,
    MatProgressSpinnerModule,
    ToggleComponent,
    QrcodeComponent,
    InfotipDirective,
  ],
})
export class NetworkSettingsPane {
  theme = 'light';
  PATH = ROUTER_LINKS;
  wifiSettings = false;
  networkConfigure: boolean = false;
  qrcodeFormGroup = new FormGroup({
    // ipv4 settings
    ip_address: new FormControl('', [ipAddressValidator]),
    subnet_mask: new FormControl(''),
    gateway: new FormControl(''),
    dns: new FormControl(''),
    // proxy server
    proxy_url: new FormControl(''),
    proxy_port: new FormControl(''),
    proxy_user_name: new FormControl(''),
    proxy_pass: new FormControl(''),
    // network time server
    ntp: new FormControl(''),
    // WiFi SSID
    wifi_ssid: new FormControl(''),
    wifi_pass: new FormControl(''),
    // MQTT
    mqtt_host: new FormControl(''),
    mqtt_port: new FormControl(1883),
  });
  qrcodeFormGroupInit = {
    // ipv4 settings
    ip_address: '',
    subnet_mask: '',
    gateway: '',
    dns: '',
    // proxy server
    proxy_url: '',
    proxy_port: '',
    proxy_user_name: '',
    proxy_pass: '',
    // network time server
    ntp: '',
    // WiFi SSID
    wifi_ssid: '',
    wifi_pass: '',
    mqtt_host: '',
    mqtt_port: 1234,
  };
  qrcodeTimeFormItems: FormItems[] = [
    {
      name: 'ntp',
      label: 'NTP',
      type: 'text',
      maxLength: '1000',
      placeholder: 'pool.ntp.org',
    },
  ];
  qrcodeIpv4FormItems: FormItems[] = [
    {
      name: 'ip_address',
      label: 'IP Address',
      type: 'text',
      maxLength: '15',
      placeholder: '192.168.0.1',
    },
    {
      name: 'gateway',
      label: 'Gateway',
      type: 'text',
      maxLength: '15',
      placeholder: '255.255.255.254',
    },
    {
      name: 'subnet_mask',
      label: 'Subnet Mask',
      type: 'text',
      maxLength: '15',
      placeholder: '255.255.255.0',
    },
    {
      name: 'dns',
      label: 'DNS',
      type: 'text',
      maxLength: '256',
      placeholder: '8.8.8.8',
    },
  ];
  qrcodeProxyFormItems: FormItems[] = [
    {
      name: 'proxy_url',
      label: 'Proxy URL',
      type: 'text',
      maxLength: '64',
      placeholder: '127.0.0.1',
    },
    {
      name: 'proxy_port',
      label: 'Proxy Port',
      type: 'text',
      maxLength: '256',
      placeholder: '7890',
    },
    {
      name: 'proxy_user_name',
      label: 'Proxy Username',
      type: 'text',
      maxLength: '256',
      placeholder: 'proxy username',
    },
    {
      name: 'proxy_pass',
      label: 'Proxy Password',
      type: 'password',
      maxLength: '256',
      placeholder: 'proxy password',
    },
  ];
  qrcodeWifiFormItems: FormItems[] = [
    {
      name: 'wifi_ssid',
      label: 'SSID',
      type: 'text',
      maxLength: '64',
      placeholder: 'Enter Wi-Fi SSID',
    },
    {
      name: 'wifi_pass',
      label: 'Password',
      type: 'password',
      maxLength: '256',
      placeholder: 'Enter Wi-Fi password',
    },
  ];

  qrLoading: boolean = false;
  qrDisplay: boolean = false;
  qrImage?: string;
  qrCreatedDate?: Date;
  qrExpiredDate?: Date;
  get features() {
    return this.featuresService.getFeatures();
  }
  @Output() qrCode = new EventEmitter();
  @Input()
  set mqttPort(newPort: number | undefined) {
    if (newPort) {
      this.qrcodeFormGroup.patchValue({
        mqtt_port: newPort,
      });
    }
  }

  constructor(
    private qrs: QrService,
    private featuresService: FeaturesService,
  ) {}

  clearAll() {
    this.qrcodeFormGroup.reset(this.qrcodeFormGroupInit);
  }

  async generateQRCode() {
    this.qrCreatedDate = new Date();
    this.qrLoading = true;
    const payload = {
      ...this.qrcodeFormGroup.value,
      auto: true,
    };
    if (!this.features.device_registration.mqtt_port) {
      delete payload.mqtt_port;
      delete payload.mqtt_host;
    }
    await this.qrs.generateQrCode(payload).then(
      (resp) => {
        this.qrImage = `data:image/jpeg;base64,${resp.contents}`;
        this.qrExpiredDate = new Date(resp.expiration_date);
        this.qrLoading = false;
        this.qrDisplay = true;
        this.qrCode.emit({
          qrCode: this.qrImage,
          qrCreatedDate: this.qrCreatedDate,
          qrExpiredDate: this.qrExpiredDate,
        });
      },
      (err) => {
        this.qrImage = '';
        this.qrLoading = false;
        this.qrDisplay = true;
      },
    );
  }

  onQrClose(event: boolean) {
    this.qrDisplay = !event;
  }
  onWifiSettingsToggle() {
    this.wifiSettings = !this.wifiSettings;
    this.qrcodeFormGroup.controls['wifi_ssid'].reset();
    this.qrcodeFormGroup.controls['wifi_pass'].reset();
  }
  onNetworkConfigToggle() {
    this.networkConfigure = !this.networkConfigure;
    this.qrcodeFormGroup.controls['ip_address'].reset();
    this.qrcodeFormGroup.controls['subnet_mask'].reset();
    this.qrcodeFormGroup.controls['gateway'].reset();
    this.qrcodeFormGroup.controls['dns'].reset();
  }
}
