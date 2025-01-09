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

import { BaseObject, SystemId } from '../common/base';
import { Classification, Detection } from '../inference/inference';
import { DeviceModuleV2 } from '../module/module';
import { Point2D } from '../drawing/drawing';

export const SENSOR_SIZE = new Point2D(4056, 3040);

export enum DeviceType {
  Type2 = '00',
  Type3 = '01',
  Type4 = '02',
  Type3W = '03',
  EdgeBox = '10',
  Undefined = '99',
  RbsRNS = '1001',
  RbsFMS = '1101',
  Empty = '',
}

export interface UpdateModuleConfigurationPayloadV2 {
  property: {
    configuration: {};
  };
}

export type DeviceConnectionState = '' | 'Disconnected' | 'Connected';
export interface DeviceGroupBase extends BaseObject {
  device_group_id: string;
  device_type: `${DeviceType}` | '';
}
export interface DeviceGroupLink extends DeviceGroupBase {
  description: string;
  ins_id: string;
  ins_date: string;
  upd_id: string;
  upd_date: string;
}
export interface DeviceBase extends BaseObject {
  device_id: SystemId;
  device_type: `${DeviceType}`;
  display_device_type: string;
  place: string;
  property: {
    device_name: SystemId;
    internal_device_id: string;
  };
  models:
    | {
        model_version_id: string;
      }[]
    | '';
  device_groups: DeviceGroupLink[];
  connectionState: DeviceConnectionState;
  lastActivityTime: string;
}
export interface DeviceListItem extends DeviceBase {}

export interface DeviceModelInfoV2 {
  model_id?: string;
  model_version_id?: string;
}

export interface DeviceGroupV2 {
  device_group_id: string;
  device_type?: string;
  comment: string;
  description: string;
  ins_id?: string;
  ins_date?: string;
  upd_id?: string;
  upd_date?: string;
}

export enum DeviceStatus {
  Connected = 'Connected',
  Disconnected = 'Disconnected',
  Periodic = 'Periodic',
  Unknown = 'Unknown',
}

export interface DeviceV2 {
  device_id: string;
  description: string;
  device_name: string;
  internal_device_id: string;
  device_type?: string;
  ins_id?: string;
  ins_date?: string;
  upd_id?: string;
  upd_date?: string;
  connection_state: DeviceStatus;
  last_activity_time?: string;
  inactivity_timeout: number;
  models?: DeviceModelInfoV2[];
  device_groups: DeviceGroupV2[];
  modules?: DeviceModuleV2[];
}

export type ROI = {
  offset: Point2D;
  size: Point2D;
};

export const DEFAULT_ROI: ROI = {
  offset: new Point2D(0, 0),
  size: SENSOR_SIZE,
};

export interface LocalDevice extends DeviceV2 {
  port: number;
  last_known_roi: ROI;
}

export function isLocalDevice(device: DeviceV2): device is LocalDevice {
  return 'port' in device;
}

export interface DeviceListV2 {
  continuation_token: string;
  devices: DeviceV2[];
}

export interface ModuleConfigurationV2 {
  property: {
    configuration: {};
    state: {};
  };
  module_id: string;
  $metadata: {};
}

// v1 and v2 api use same minimal response,
// v1 use comment, v2 use description
// keep both
export interface MinimalDeviceListItem {
  device_id: string;
  device_type?: `${DeviceType}`;
  display_device_type?: string;
  place?: string;
  comment: string;
  description: string;
  ins_id?: string;
  ins_date?: string;
  upd_id?: string;
  upd_date?: string;
  property: {
    device_name: string;
    internal_device_id: string;
  };
  connection_state: string;
  device_groups: MinimalDeviceListItemGroup[];
}

export interface MinimalDeviceListItemGroup {
  device_group_id: string;
  description: string;
  comment: string;
  device_type: string;
}

export interface DeviceFrame {
  image: string;
  inference?: Classification | Detection;
}
