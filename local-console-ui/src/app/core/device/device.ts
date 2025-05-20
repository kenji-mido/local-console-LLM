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

import { Point2D } from '../drawing/drawing';
import { InferenceLike } from '../inference/inference';
import { DeviceModuleV2, isSysModule } from '../module/module';

export const SENSOR_SIZE = new Point2D(2028, 1520);
export const SYSTEM_MODULE_ID = '$system';

export interface DeviceModelInfoV2 {
  model_id?: string;
  model_version_id?: string;
}

export enum DeviceStatus {
  Connected = 'Connected',
  Disconnected = 'Disconnected',
  Periodic = 'Periodic',
  Connecting = 'Connecting',
}

export enum DeviceArchetype {
  UNKNOWN,
  T3,
  T5,
  RASPI,
}

export enum DeviceType {
  T3P_LUCID = 'SZP123S-001',
  T3P_RAYPRUS = 'CSV26',
  T3WS = 'AIH-IVRW2',
  T5 = 'AIH-IPRSW',
  RASPI = 'Raspberry Pi',
  UNKNOWN = 'unknown',
}

export interface LocalDevice {
  device_id: string;
  description: string;
  device_name: string;
  device_type: string;
  ins_id?: string;
  ins_date?: string;
  upd_id?: string;
  upd_date?: string;
  connection_state: DeviceStatus;
  last_activity_time?: string;
  inactivity_timeout: number;
  models?: DeviceModelInfoV2[];
  modules?: DeviceModuleV2[];
  last_known_roi: ROI;
}

export type ROI = {
  offset: Point2D;
  size: Point2D;
};

export const DEFAULT_ROI: ROI = {
  offset: new Point2D(0, 0),
  size: SENSOR_SIZE,
};

export interface DeviceListV2 {
  continuation_token: string;
  devices: LocalDevice[];
}

export interface DeviceFrame {
  image: string;
  inference?: InferenceLike;
  identifier: string;
}

export interface UpdateModuleConfigurationPayloadV2 {
  configuration: {};
}

export interface ModuleConfigurationV2 {
  property: {
    configuration: {};
    state: {};
  };
  module_id: string;
  $metadata: {};
}

export function getSystemModule(device: LocalDevice) {
  const mod = device.modules?.find(isSysModule);
  if (mod && isSysModule(mod)) return mod;
  return undefined;
}

export function deviceTypeToArchetype(deviceType?: string): DeviceArchetype {
  switch (deviceType) {
    case DeviceType.T3P_LUCID:
    case DeviceType.T3P_RAYPRUS:
    case DeviceType.T3WS:
      return DeviceArchetype.T3;
    case DeviceType.T5:
      return DeviceArchetype.T5;
    case DeviceType.RASPI:
      return DeviceArchetype.RASPI;
  }
  return DeviceArchetype.UNKNOWN;
}
