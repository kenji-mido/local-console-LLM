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
import { ToggleComponent } from '../../components/toggle/toggle.component';

interface NetworkInfoTabItems {
  broker: string | undefined;
  port: number | undefined;
  ntpServer: string | undefined;
  static: boolean;
  ipAddress: string | undefined;
  subnetMask: string | undefined;
  gateway: string | undefined;
  DNS: string | undefined;
  proxyUrl: string | undefined;
  proxyPort: number | undefined;
  proxyUsername: string | undefined;
  proxyPassword: string | undefined;
  ssid: string | undefined;
  passPhrase: string | undefined;
}

export function replaceAsterisks(
  input: string | undefined,
): string | undefined {
  if (input == undefined) {
    return undefined;
  }

  return '*'.repeat(input.length);
}
@Component({
  selector: 'app-network-info',
  templateUrl: './network-info.component.html',
  styleUrls: ['./network-info.component.scss'],
  standalone: true,
  imports: [CommonModule, CardComponent, ToggleComponent],
})
export class NetworkInfo {
  network_info: NetworkInfoTabItems = {
    broker: undefined,
    port: undefined,
    ntpServer: undefined,
    static: true,
    ipAddress: undefined,
    subnetMask: undefined,
    gateway: undefined,
    DNS: undefined,
    proxyUrl: undefined,
    proxyPort: undefined,
    proxyUsername: undefined,
    proxyPassword: undefined,
    ssid: undefined,
    passPhrase: undefined,
  };

  @Input() device: DeviceV2 | null = null;

  ngOnChanges(changes: SimpleChanges) {
    this.onDeviceInfoReceived(changes['device'].currentValue);
  }
  onDeviceInfoReceived(device: DeviceV2 | null) {
    if (
      device === null ||
      device.modules === null ||
      !isSysModuleState(device.modules?.[0].property.state!)
    ) {
      this.network_info = {
        broker: undefined,
        port: undefined,
        ntpServer: undefined,
        static: true,
        ipAddress: undefined,
        subnetMask: undefined,
        gateway: undefined,
        DNS: undefined,
        proxyUrl: undefined,
        proxyPort: undefined,
        proxyUsername: undefined,
        proxyPassword: undefined,
        ssid: undefined,
        passPhrase: undefined,
      };
      return;
    }
    const deviceState: SysAppModuleStateV2 =
      device.modules?.[0].property.state!;
    this.network_info = {
      broker: deviceState.PRIVATE_endpoint_settings?.endpoint_url,
      port: deviceState.PRIVATE_endpoint_settings?.endpoint_port,
      ntpServer: deviceState.network_settings?.ntp_url,
      static:
        deviceState.periodic_setting?.ip_addr_setting?.toLowerCase() !== 'dhcp',
      ipAddress: deviceState.network_settings?.ip_address,
      subnetMask: deviceState.network_settings?.subnet_mask,
      gateway: deviceState.network_settings?.gateway_address,
      DNS: deviceState.network_settings?.dns_address,
      proxyUrl: deviceState.network_settings?.proxy_url,
      proxyPort: deviceState.network_settings?.proxy_port,
      proxyUsername: deviceState.network_settings?.proxy_user_name,
      proxyPassword: replaceAsterisks(
        deviceState.network_settings?.proxy_password,
      ),
      ssid: deviceState.wireless_setting?.sta_mode_setting?.ssid,
      passPhrase: replaceAsterisks(
        deviceState.wireless_setting?.sta_mode_setting?.password,
      ),
    };
  }
}
