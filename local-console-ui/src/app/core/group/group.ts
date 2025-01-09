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

import { BaseObject } from '../common/base';
import { DeviceType, MinimalDeviceListItem } from '../device/device';

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
export interface DeviceGroup extends DeviceGroupLink {
  devices: MinimalDeviceListItem[];
}
export interface DeviceGroupList {
  device_groups: DeviceGroup[];
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

export interface DeviceGroupListV2 {
  continuation_token: string;
  device_groups: DeviceGroup[];
}
