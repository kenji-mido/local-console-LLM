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

import { Injectable } from '@angular/core';
import { HttpParams } from '@angular/common/http';
import { HttpApiClient } from '../common/http/http';
import { DeviceGroup, DeviceGroupList, DeviceGroupListV2 } from './group';
import { environment } from '../../../environments/environment';
import { makeUrlQuery } from '../common/http/http.utils';

export interface DeviceGroupPayload {
  device_group_id?: string;
  comment: string;
  device_id: string;
  del_from_dgroup: string;
}

export interface DeviceGroupPayloadV2 {
  device_group_id?: string;
  description: string;
  device_id: string;
  del_from_dgroup: string;
}

const paths = {
  devices: '/devices',
  deviceGroups: '/devicegroups',
};

@Injectable({
  providedIn: 'root',
})
export class GroupService {
  private deviceGroupPath = environment.apiUrl + paths.deviceGroups;
  private deviceGroupDetailPath = `${environment.apiUrl}${paths.devices}?scope=minimal`;
  private deviceGroupPathV2 = environment.apiV2Url + paths.deviceGroups;
  private deviceGroupDetailPathV2 = `${environment.apiV2Url}${paths.devices}?scope=minimal`;

  constructor(private http: HttpApiClient) {}

  getGroups() {
    return this.http.get<DeviceGroupList>(this.deviceGroupPath);
  }

  getGroup(groupId: string) {
    return this.http.get<DeviceGroup>(
      `${this.deviceGroupDetailPath}&device_group_id=${groupId}`,
    );
  }

  addGroup(payload: DeviceGroupPayload) {
    const url = makeUrlQuery(this.deviceGroupPath, payload);
    return this.http.post<any>(url.href, payload);
  }

  updateGroup(payload: DeviceGroupPayload) {
    if (!payload.device_id) {
      payload.device_id = '@@nullupdate';
    }
    if (!payload.comment) {
      payload.comment = '@@nullupdate';
    }
    const url = makeUrlQuery(
      `${this.deviceGroupPath}/${payload.device_group_id}`,
      payload,
    );
    return this.http.patch<any>(url.href, payload);
  }

  deleteGroup(groupId: string) {
    return this.http.delete<any>(`${this.deviceGroupPath}/${groupId}`);
  }

  // Add V2 function
  getGroupsV2(limit = 100, startingAfter = '') {
    let httpParams = new HttpParams().set('limit', limit);
    if (startingAfter && startingAfter.length > 0) {
      httpParams = httpParams.append('starting_after', startingAfter);
    }
    return this.http.get<DeviceGroupListV2>(this.deviceGroupPathV2, httpParams);
  }

  getGroupV2(groupId: string) {
    return this.http.get<DeviceGroup>(
      `${this.deviceGroupDetailPathV2}&device_group_id=${groupId}`,
    );
  }

  getDeviceGroupV2(groupId: string) {
    return this.http.get<DeviceGroup>(`${this.deviceGroupPathV2}/${groupId}`);
  }

  addGroupV2(payload: DeviceGroupPayloadV2) {
    const url = makeUrlQuery(this.deviceGroupPathV2, payload);
    return this.http.post<any>(url.href, payload);
  }

  updateGroupV2(payload: DeviceGroupPayloadV2) {
    if (!payload.device_id) {
      payload.device_id = '@@nullupdate';
    }
    if (!payload.description) {
      payload.description = '@@nullupdate';
    }
    const url = makeUrlQuery(
      `${this.deviceGroupPathV2}/${payload.device_group_id}`,
      payload,
    );
    return this.http.patch<any>(url.href, payload);
  }

  deleteGroupV2(groupId: string) {
    return this.http.delete<any>(`${this.deviceGroupPathV2}/${groupId}`);
  }
}
