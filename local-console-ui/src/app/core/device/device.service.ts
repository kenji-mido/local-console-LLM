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

import { Dialog } from '@angular/cdk/dialog';
import { HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import {
  DeviceSelectionPopupComponent,
  DeviceSelectionPopupData,
} from '@app/core/device/device-selector/device-selector-popup.component';
import { firstValueFrom, ReplaySubject } from 'rxjs';
import { CommandService } from '../command/command.service';
import { EnvService } from '../common/environment.service';
import { HttpApiClient } from '../common/http/http';
import { Configuration } from './configuration';
import {
  DEFAULT_ROI,
  DeviceListV2,
  LocalDevice,
  ModuleConfigurationV2,
  ROI,
  UpdateModuleConfigurationPayloadV2,
} from './device';

@Injectable({
  providedIn: 'root',
})
export class DeviceService {
  private __lastKnownROICache = new Map<string, ROI>();
  private devicesSubject = new ReplaySubject<LocalDevice[]>(1);
  public devices$ = this.devicesSubject.asObservable();

  constructor(
    private commands: CommandService,
    private http: HttpApiClient,
    private dialog: Dialog,
    private envService: EnvService,
  ) {}

  get devicePathV2() {
    return `${this.envService.getApiUrl()}/devices`;
  }

  async getDevicesV2(
    ids?: string[],
    limit = 500,
    startingAfter = '',
  ): Promise<DeviceListV2> {
    if (ids && ids.length) {
      let queryParams = new HttpParams();
      queryParams = queryParams.append('device_ids', ids.join(','));
      return this.http.get<DeviceListV2>(this.devicePathV2, queryParams);
    } else {
      let httpParams = new HttpParams().set('limit', limit);
      if (startingAfter && startingAfter.length > 0) {
        httpParams = httpParams.append('starting_after', startingAfter);
      }
      return this.http.get<DeviceListV2>(this.devicePathV2, httpParams);
    }
  }

  getDevice(id: string, silent = false) {
    return this.http
      .get<LocalDevice>(`${this.devicePathV2}/${id}`, {}, !silent)
      .then(this.patchLocalDeviceCachedROI.bind(this));
  }

  async updateDeviceName(device_id: string, device_name: string) {
    const updateResp = await this.http.patch<any>(
      `${this.devicePathV2}/${device_id}?new_name=${device_name}`,
      {},
    );
    return updateResp;
  }

  async deleteDevice(device: LocalDevice) {
    const result = await this.http.delete(
      `${this.devicePathV2}/${device.device_id}`,
    );
    await this.loadDevices();
    return result;
  }

  async createDevice(device_name: string, mqtt_port: number) {
    var result = {};
    try {
      result = await this.http.post(`${this.devicePathV2}`, {
        device_name,
        id: mqtt_port,
      });
    } catch (err) {
      console.error('Could not register the device', err);
      return null;
    }
    await this.loadDevices();
    return result;
  }

  async loadDevices() {
    // This whole function might need to be throttled + debounced
    try {
      const devices = (await this.getDevicesV2()).devices;
      const patchedDevices = devices.map((d) =>
        this.patchLocalDeviceCachedROI(d),
      );
      this.devicesSubject.next(patchedDevices);
    } catch (err) {
      console.error('Could not update device list', err);
    }
  }

  async askForDeviceSelection(selectedDevice?: LocalDevice) {
    const data = <DeviceSelectionPopupData>{
      selectedDevice,
    };
    const dRef = this.dialog.open(DeviceSelectionPopupComponent, {
      data,
      panelClass: 'extended',
    });
    return (await firstValueFrom(dRef.closed)) as LocalDevice | undefined;
  }

  async updateModuleConfigurationV2(
    device_id: string,
    module_id: string,
    payload: UpdateModuleConfigurationPayloadV2,
  ) {
    const moduleResp = await this.http.patch<ModuleConfigurationV2>(
      `${this.devicePathV2}/${device_id}/modules/${module_id}/property`,
      payload,
    );
    return moduleResp;
  }

  async patchConfiguration(
    device_id: string,
    configuration: Configuration,
    dry_run: boolean = false,
  ): Promise<Configuration> {
    // TODO: handle error
    return await this.http.patch(
      `${this.devicePathV2}/${device_id}/configuration?dry_run=${dry_run}`,
      configuration,
    );
  }
  async getConfiguration(device_id: string): Promise<Configuration> {
    // TODO: handle error
    return await this.http.get<Configuration>(
      `${this.devicePathV2}/${device_id}/configuration`,
    );
  }

  setLastKnownRoiCache(deviceId: string, roi: ROI) {
    this.__lastKnownROICache.set(deviceId, roi);
  }

  getLastKnownRoiCache(deviceId: string) {
    return this.__lastKnownROICache.get(deviceId) || DEFAULT_ROI;
  }

  private patchLocalDeviceCachedROI(device: LocalDevice) {
    device.last_known_roi = this.getLastKnownRoiCache(device.device_id);
    return device;
  }
}
