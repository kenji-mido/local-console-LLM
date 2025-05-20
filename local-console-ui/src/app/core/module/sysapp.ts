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

import { DTDLReqInfoV2, DTDLResInfoV2 } from './dtdl';

export function isSysModuleConfig(config: any): config is SysAppModuleConfigV2 {
  return config && 'device_info' in config;
}

export interface SysAppModuleStateV2 {
  PRIVATE_endpoint_settings?: SysAppModuleEndpointSettingV2;
  system_settings?: SysAppModuleSystemSettingsV2;
  device_capabilities?: SysAppModuleDeviceCapabilitiesV2;
  PRIVATE_reserved?: SysAppModuleReservedV2;
  wireless_setting?: SysAppModuleWirelessSettingV2;
  placeholder?: SysAppModulePlaceholderV2;
}

export interface SysAppModuleConfigV2 {
  device_state?: SysAppModuleDeviceStatesV2;
  device_info?: SysAppModuleDeviceInfoV2;
  network_settings?: SysAppModuleNetworkSettingV2;
  periodic_setting?: PeriodicSettingV2;
}

export function isSysModuleState(state: any): state is SysAppModuleStateV2 {
  return state && 'PRIVATE_endpoint_settings' in state;
}

// Module: system app
// configuration:
// - device_status
export interface SysAppModuleDeviceStatesV2 {
  req_info?: DTDLReqInfoV2;
  power_states?: SysAppModuleStatePowerStateV2;
  process_state?: string;
  hours_meter?: number;
  res_info?: DTDLResInfoV2;
}

export interface SysAppModuleStatePowerStateV2 {
  power_source?: number;
  power_level?: number;
  is_secondary_used?: boolean;
}

// Module: system app
// state:
// - PRIVATE_endpoint_settings
export interface SysAppModuleEndpointSettingV2 {
  req_info?: DTDLReqInfoV2;
  endpoint_url?: string;
  endpoint_port?: number;
  protocol_version?: string;
  res_info?: DTDLResInfoV2;
}

// Module: system app
// state:
// - system_settings
export interface SysAppModuleSystemSettingsV2 {
  req_info?: DTDLReqInfoV2;
  operation_mode?: number;
  periodic_config?: SysAppModulePeriodicConfigV2;
  is_led_active?: boolean;
  factory_reset_enabled?: boolean;
  log_settings?: SysAppModuleLogV2[];
  temperature_update_interval?: number;
  res_info?: DTDLResInfoV2;
}

export interface SysAppModuleLogV2 {
  filter?: number;
  level?: number;
  destination?: number;
  storage_url?: string;
  storage_name?: string;
  file_path?: string;
}

export interface SysAppModulePeriodicConfigV2 {
  operation_mode?: number;
  recovery_method?: number;
  interval_settings?: SysAppModulePeriodicConfigIntervalV2[];
  ip_addr_setting?: string;
}

export interface SysAppModulePeriodicConfigIntervalV2 {
  base_time?: string;
  capture_interval?: number;
  config_interval?: number;
}

// Module: system app
// state:
// - device_capabilities
export interface SysAppModuleDeviceCapabilitiesV2 {
  req_info?: DTDLReqInfoV2;
  is_battery_supported?: boolean;
  supported_wireless_mode?: number;
  is_periodic_supported?: boolean;
  is_sensor_postprocess_supported?: boolean;
  res_info?: DTDLResInfoV2;
}

// Module: system app
// state:
// - device_info
export interface SysAppModuleDeviceInfoV2 {
  model_name?: string;
  processors?: SysAppModuleProcessorV2[];
  sensors?: SysAppModuleSensorV2[];
  ai_models?: SysAppModuleStateAiModelV2[];
}

export interface SysAppModuleProcessorV2 {
  name?: string;
  loader_version?: string;
  firmware_version?: string;
  update_date_firmware?: string;
}

export interface SysAppModuleStateAiModelV2 {
  name?: string;
  version?: string;
  converter_version?: string;
}

export interface SysAppModuleSensorV2 {
  name?: string;
  id?: string;
  hardware_version?: string;
  current_temperature?: number;
  highest_temperature?: number;
  loader_version?: string;
  update_date_loader?: string;
  firmware_version?: string;
  update_date_firmware?: string;
  calibration_params?: SysAppModuleStateSensorCalibrationParamsV2[];
}

export interface SysAppModuleStateSensorCalibrationParamsV2 {
  name?: string;
  mode?: number;
  version?: string;
}

// Module: system app
// state:
// - PRIVATE_reserved
export interface SysAppModuleReservedV2 {
  schema?: string;
}

// Module: system app
// state:
// - wireless_setting
export interface SysAppModuleWirelessSettingV2 {
  req_info?: DTDLReqInfoV2;
  sta_mode_setting?: SysAppModuleStateWirelessStaModeV2;
  ap_mode_setting?: SysAppModuleStateWirelessApModeV2;
  res_info?: DTDLResInfoV2;
}

export interface SysAppModuleStateWirelessStaModeV2 {
  ssid?: string;
  password?: string;
  encryption?: number;
}

export interface SysAppModuleStateWirelessApModeV2 {
  ssid?: string;
  password?: string;
  encryption?: number;
  channel?: number;
}

// Module: system app
// state:
// - placeholder
export interface SysAppModulePlaceholderV2 {
  Version?: {
    CameraSetupFileVersion?: {
      ColorMatrixStd?: string;
      ColorMatrixCustom?: string;
      GammaStd?: string;
      GammaCustom?: string;
      LSCISPStd?: string;
      LSCISPCustom?: string;
      LSCRawStd?: string;
      LSCRawCustom?: string;
      PreWBStd?: string;
      PreWBCustom?: string;
      DewarpStd?: string;
      DewarpCustom?: string;
    };
  };
}

// Module: system app
// state:
//  network_setting
export interface SysAppModuleNetworkSettingV2 {
  req_info?: DTDLReqInfoV2;
  proxy_url?: string;
  proxy_port?: number;
  proxy_user_name?: string;
  proxy_password?: string;
  ip_address?: string;
  subnet_mask?: string;
  gateway_address?: string;
  dns_address?: string;
  ntp_url?: string;
  res_info?: DTDLResInfoV2;
}

export interface PeriodicSettingV2 {
  ip_addr_setting?: string;
}
