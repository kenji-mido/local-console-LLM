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
  DEFAULT_ROI,
  DeviceFrame,
  DeviceListV2,
  DeviceStatus,
  DeviceV2,
  LocalDevice,
} from '@app/core/device/device';
import {
  SysAppModuleNetworkSettingV2,
  SysAppModuleEndpointSettingV2,
  SysAppModuleWirelessSettingV2,
} from '@app/core/module/sysapp';
import { DeviceModuleV2 } from '@app/core/module/module';
import {
  Classification,
  ClassificationItem,
  Detection,
} from '@app/core/inference/inference';
import { Inferences, InferenceType } from './inferences';
import { SMALLEST_VALID_PNG } from './qr';

export module DeviceList {
  export function sample(): DeviceListV2 {
    return {
      continuation_token: '',
      devices: [
        Device.sample('first_device', '001', DeviceStatus.Connected),
        Device.sample('second_device', '002', DeviceStatus.Disconnected),
        Device.sample('third_device', '003', DeviceStatus.Periodic),
      ],
    };
  }

  export function sampleLocal(): DeviceListV2 {
    const list = sample();
    list.devices = list.devices.map((device, i) => {
      return Device.sampleLocal(device, 1884 + i);
    });
    return list;
  }

  export function sampleEmpty(): DeviceListV2 {
    return {
      continuation_token: '',
      devices: [],
    };
  }
}

export module Device {
  export function sample(
    device_name: string = 'device_xyz',
    device_id: string = '000',
    state: DeviceStatus = DeviceStatus.Connected,
  ): DeviceV2 {
    return {
      device_name,
      device_id: device_id,
      description: 'Mocked device',
      internal_device_id: '000',
      inactivity_timeout: 0,
      device_groups: [],
      connection_state: state,
      modules: [DeviceModule.sampleSystem()],
    };
  }

  export function sampleLocal(): LocalDevice;
  export function sampleLocal(device: DeviceV2, port: number): LocalDevice;
  export function sampleLocal(device?: DeviceV2, port?: number): LocalDevice {
    if (device && port) {
      return <LocalDevice>{ ...device, port, last_known_roi: DEFAULT_ROI };
    } else {
      return sampleLocal(sample(), 1234);
    }
  }

  export function sampleFrame(type: InferenceType = 'classification') {
    return <DeviceFrame>{
      image: 'data:image/jpeg;base64,' + SMALLEST_VALID_PNG,
      inference: Inferences.sample(type),
    };
  }
}

export module DeviceModule {
  export function sampleSystem(): DeviceModuleV2 {
    return {
      module_name: 'SYSTEM',
      module_id: '$system',
      property: {
        state: {
          network_settings: NetworkSettings.sampleSettings(),
          wireless_setting: WirelessSettings.sampleSettings(),
          PRIVATE_endpoint_settings: EndpointSettings.sampleSettings(),
          device_info: {
            sensors: [{ firmware_version: '020000', name: 'IMX500' }],
            processors: [{ firmware_version: 'D52408' }],
            ai_models: [
              {
                name: 'id 1',
                version: 'version1',
                converter_version: 'conv_version_1',
              },
              {
                name: 'id 2',
                version: 'version2',
                converter_version: 'conv_version_2',
              },
            ],
          },
          PRIVATE_reserved: {},
        },
      },
    };
  }
}

export module NetworkSettings {
  export function sampleSettings(): SysAppModuleNetworkSettingV2 {
    return {
      proxy_url: 'mock_value',
      proxy_port: 1000,
      proxy_user_name: 'mock_value',
      proxy_password: 'mock_value',
      ip_address: 'mock_value',
      subnet_mask: 'mock_value',
      gateway_address: 'mock_value',
      dns_address: 'mock_value',
      ntp_url: 'mock_value',
    };
  }
}

export module EndpointSettings {
  export function sampleSettings(): SysAppModuleEndpointSettingV2 {
    return {
      endpoint_url: 'mock_value',
      endpoint_port: 1000,
    };
  }
}

export module WirelessSettings {
  export function sampleSettings(): SysAppModuleWirelessSettingV2 {
    return {
      sta_mode_setting: {
        ssid: 'ssid',
        password: 'password_ssid',
      },
    };
  }
}
