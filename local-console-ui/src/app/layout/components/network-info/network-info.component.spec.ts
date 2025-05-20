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

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LocalDevice } from '@app/core/device/device';
import { EdgeAppModuleStateV2 } from '@app/core/module/edgeapp';
import {
  SysAppModuleConfigV2,
  SysAppModuleStateV2,
  isSysModuleConfig,
  isSysModuleState,
} from '@app/core/module/sysapp';
import { Device } from '@samplers/device';
import { NetworkInfo, replaceAsterisks } from './network-info.component';

describe('DeviceInfoComponent', () => {
  let component: NetworkInfo;
  let fixture: ComponentFixture<NetworkInfo>;
  const network_info_null = {
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

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NetworkInfo],
    }).compileComponents();

    fixture = TestBed.createComponent(NetworkInfo);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  describe('onNetworkInfoReceived', () => {
    it('should define all elements undefined if device is null', () => {
      const device: LocalDevice | null = null;
      component.onDeviceInfoReceived(device);
      expect(component.network_info).toEqual(network_info_null);
    });
    it('should define all elements undefined if modules is null', () => {
      let device: LocalDevice | null = Device.sample();
      device.modules = undefined;
      component.onDeviceInfoReceived(device);
      expect(component.network_info).toEqual(network_info_null);
    });
    it('should define all elements undefined if not sysmodules', () => {
      let device: LocalDevice | null = Device.sample();
      const edge_app_state: EdgeAppModuleStateV2 = { edge_app: undefined };
      if (device.modules?.[0].property.state) {
        device.modules[0].property.state = edge_app_state;
      }
      component.onDeviceInfoReceived(device);
      expect(component.network_info).toEqual(network_info_null);
    });
    it('should define all elements correctly', () => {
      let device: LocalDevice | null = Device.sample();
      component.onDeviceInfoReceived(device);
      if (
        isSysModuleState(device.modules?.[0].property.state!) &&
        isSysModuleConfig(device.modules?.[0].property.configuration!)
      ) {
        let deviceState: SysAppModuleStateV2 =
          device.modules?.[0].property.state!;
        let deviceConfig: SysAppModuleConfigV2 =
          device.modules?.[0].property.configuration!;

        expect(component.network_info.broker).toEqual(
          deviceState.PRIVATE_endpoint_settings?.endpoint_url,
        );
        expect(component.network_info.port).toEqual(
          deviceState.PRIVATE_endpoint_settings?.endpoint_port,
        );
        expect(component.network_info.ntpServer).toEqual(
          deviceConfig.network_settings?.ntp_url,
        );
        expect(component.network_info.static).toEqual(true);
        expect(component.network_info.ipAddress).toEqual(
          deviceConfig.network_settings?.ip_address,
        );
        expect(component.network_info.subnetMask).toEqual(
          deviceConfig.network_settings?.subnet_mask,
        );
        expect(component.network_info.gateway).toEqual(
          deviceConfig.network_settings?.gateway_address,
        );
        expect(component.network_info.DNS).toEqual(
          deviceConfig.network_settings?.dns_address,
        );
        expect(component.network_info.proxyUrl).toEqual(
          deviceConfig.network_settings?.proxy_url,
        );
        expect(component.network_info.proxyPort).toEqual(
          deviceConfig.network_settings?.proxy_port,
        );
        expect(component.network_info.proxyUsername).toEqual(
          deviceConfig.network_settings?.proxy_user_name,
        );
        expect(component.network_info.proxyPassword).toEqual(
          replaceAsterisks(deviceConfig.network_settings?.proxy_password),
        );
        expect(component.network_info.ssid).toEqual(
          deviceState.wireless_setting?.sta_mode_setting?.ssid,
        );
        expect(component.network_info.passPhrase).toEqual(
          replaceAsterisks(
            deviceState.wireless_setting?.sta_mode_setting?.password,
          ),
        );
      }
    });
  });
});
