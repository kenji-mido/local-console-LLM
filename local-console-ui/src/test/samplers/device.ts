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
  DeviceType,
  LocalDevice,
} from '@app/core/device/device';
import { EdgeAppModuleEdgeAppCustomSettingsV2 } from '@app/core/module/edgeapp';
import { DeviceModuleV2 } from '@app/core/module/module';
import {
  SysAppModuleEndpointSettingV2,
  SysAppModuleNetworkSettingV2,
  SysAppModuleWirelessSettingV2,
} from '@app/core/module/sysapp';
import { Inferences, InferenceType } from './inferences';
import { SMALLEST_VALID_PNG } from './qr';

export namespace DeviceList {
  export function sample(): DeviceListV2 {
    return {
      continuation_token: '',
      devices: [
        Device.sample({
          device_name: 'first_device',
          device_id: '1884',
          connection_state: DeviceStatus.Connected,
        }),
        Device.sample({
          device_name: 'second_device',
          device_id: '1885',
          connection_state: DeviceStatus.Disconnected,
        }),
        Device.sample({
          device_name: 'third_device',
          device_id: '1886',
          connection_state: DeviceStatus.Connecting,
        }),
        Device.sample({
          device_name: 'raspi',
          device_id: '1887',
          connection_state: DeviceStatus.Connected,
          device_type: DeviceType.RASPI,
        }),
      ],
    };
  }

  export function sampleEmpty(): DeviceListV2 {
    return {
      continuation_token: '',
      devices: [],
    };
  }
}

export namespace Device {
  export function sample(values: Partial<LocalDevice> = {}): LocalDevice {
    return {
      device_name: 'device_xyz',
      device_id: '1883',
      device_type: 'SZP123S-001',
      description: 'Mocked device',
      inactivity_timeout: 0,
      connection_state: DeviceStatus.Connected,
      modules: [DeviceModule.sampleSystem()],
      last_known_roi: DEFAULT_ROI,
      ...values,
    };
  }

  export function sampleFrame(type: InferenceType = 'classification') {
    return <DeviceFrame>{
      image: 'data:image/jpeg;base64,' + SMALLEST_VALID_PNG,
      inference: Inferences.sample(type),
    };
  }
}

export module DeviceModule {
  export function sampleEdgeAppPropertyCustomConfig(): {
    custom_settings: EdgeAppModuleEdgeAppCustomSettingsV2;
  } {
    return {
      custom_settings: {
        ai_models: {
          one_pass_model: {
            parameters: {
              max_detections: 3,
            },
          },
        },
      },
    };
  }
  export function sampleSystem(): DeviceModuleV2 {
    return {
      property: {
        configuration: {
          network_settings: NetworkSettings.sampleSettings(),
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
        },
        state: {
          wireless_setting: WirelessSettings.sampleSettings(),
          PRIVATE_endpoint_settings: EndpointSettings.sampleSettings(),
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
