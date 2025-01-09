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

import { Injectable, Signal, computed, signal } from '@angular/core';
import { Observable, BehaviorSubject } from 'rxjs';
import { DeviceService } from './device/device.service';
import { assertNotEmpty } from './common/validation';
import {
  EdgeAppModuleConfigurationV2,
  UpdateModuleConfigurationPayloadV2,
} from './device/device';
import { InferenceCommand } from './command/command';

export interface UIDevice {
  // MUST property for UI
  device_name: string;
  device_status: string;
  device_id: string;
  device_description: string;
  device_create_time: string;
  // TODO: Current we don't know final API other part still TBD
  // Below is useless for UI
  // But keep this property for feature usage
  device_type: string;
}

export interface UIDeviceGroup {
  // MUST property for UI
  group_name: string;
  group_description: string;

  // TODO: Current we don't know final API other part still TBD
  // Below is useless for UI
  // But keep this property for feature usage

  // UIDevice list
  devices: UIDevice[];
}

const dialogSelectedDevices: Array<string> = [];
const inferenceSelectedDevices: Array<string> = [];
const screenSelectedDeviceType: string = '';

@Injectable({
  providedIn: 'root',
})
export class HubUIDeviceService {
  private dialogSelectedDevices$ = new BehaviorSubject(dialogSelectedDevices);
  private screenSelectedDeviceType$ = new BehaviorSubject(
    screenSelectedDeviceType,
  );
  private inferenceSelectedDevices$ = new BehaviorSubject(
    inferenceSelectedDevices,
  );
  private uiInferenceConfiguration$ = new BehaviorSubject<string>('');
  private deviceTypeList$ = new BehaviorSubject<Array<string>>([]);

  // data
  private deviceGroups = <UIDeviceGroup[]>[];
  private userSelectedUIDevices = signal<UIDevice[]>([]);

  // Observable
  private deviceGroups$ = new Observable<UIDeviceGroup[]>();

  constructor(private deviceService: DeviceService) {}

  getDeviceGroups(): Observable<UIDeviceGroup[]> {
    return this.deviceGroups$;
  }

  sortDeviceByName() {}
  sortDeviceByStatus() {}
  sortDeviceByID() {}
  sortDeviceByDescription() {}
  sortDeviceByCreateTime() {}

  addDevice(device: UIDevice): void {
    this.userSelectedUIDevices.update((devices) => [...devices, device]);
  }

  removeDevice(deviceId: string): void {
    const updatedUserSelectedUIDevices = this.userSelectedUIDevices().filter(
      (device) => device.device_id != deviceId,
    );
    this.userSelectedUIDevices.set(updatedUserSelectedUIDevices);
  }

  selectAllDevices(): void {
    let devices: UIDevice[] = [];
    this.deviceGroups.map((g) => (devices = [...devices, ...g.devices]));
    const uniqDevices = <UIDevice[]>this.makeUniqArray(devices);
    this.userSelectedUIDevices.set(uniqDevices);
  }

  selectGroupDevices(group_name: string) {
    const groups = this.deviceGroups.filter((g) => g.group_name == group_name);
    // This part assume there will not groups share same group_id
    const devices = [...this.userSelectedUIDevices(), ...groups[0].devices];
    const uniqDevices = <UIDevice[]>this.makeUniqArray(devices);
    this.userSelectedUIDevices.set(uniqDevices);
  }

  getUserSelectedDevices(): Signal<UIDevice[]> {
    return computed(this.userSelectedUIDevices);
  }

  // TODO: Consider in the near future move all util function to Util.ts
  // Due to in current SCS 1 device may belongs to several groups
  // If we collect devices from several groups, it is possible we collect duplicated devices
  // So we need remove them.
  makeUniqArray(array: unknown[]): unknown[] {
    return Array.from(new Set(array));
  }

  // For select device dialog
  getDialogSelectedDevices(): Observable<Array<string>> {
    return this.dialogSelectedDevices$.asObservable();
  }

  setDialogSelectedDevices(devices: Array<string>) {
    this.dialogSelectedDevices$.next(devices);
  }

  // For device type
  getScreenSelectedDeviceType(): Observable<string> {
    return this.screenSelectedDeviceType$.asObservable();
  }

  setScreenSelectedDeviceType(type: string) {
    this.screenSelectedDeviceType$.next(type);
  }

  // For inference select devices
  getInferenceSelectedDevices(): Observable<Array<string>> {
    return this.inferenceSelectedDevices$.asObservable();
  }

  setInferenceSelectedDevices(devices: Array<string>) {
    this.inferenceSelectedDevices$.next(devices);
  }

  // For device inference
  // TODO: current useless due to no spec can clear describe how to set configuration
  getUIInferenceConfiguration(): Observable<string> {
    return this.uiInferenceConfiguration$.asObservable();
  }

  setUIInferenceConfiguration(configuration: string) {
    this.uiInferenceConfiguration$.next(configuration);
  }

  startUploadInference() {
    this.inferenceSelectedDevices$.value.forEach((d) => {
      this.deviceService.getDeviceV2(d).then((data) => {
        data.modules?.forEach((m) => {
          if (m.module_name && m.module_name.startsWith('EdgeApp')) {
            assertNotEmpty(m.module_id);
            const configObject = <EdgeAppModuleConfigurationV2>(
              JSON.parse(this.uiInferenceConfiguration$.value)
            );
            assertNotEmpty(configObject.edge_app);
            assertNotEmpty(configObject.edge_app.common_settings);
            assertNotEmpty(configObject.edge_app.common_settings.process_state);
            configObject.edge_app.common_settings.process_state =
              InferenceCommand.START;
            const payload: UpdateModuleConfigurationPayloadV2 = {
              property: {
                configuration: configObject,
              },
            };
            //[FIX ME] change replaceModuleConfigurationV2 in v1.7.1
            this.deviceService.updateModuleConfigurationV2(
              d,
              m.module_id,
              payload,
            );
          }
        });
      });
    });
  }

  stopUploadInference() {
    this.inferenceSelectedDevices$.value.forEach((d) => {
      this.deviceService.getDeviceV2(d).then((data) => {
        data.modules?.forEach((m) => {
          if (m.module_name && m.module_name.startsWith('EdgeApp')) {
            assertNotEmpty(m.module_id);
            this.deviceService.stopUploadInferenceResultV2(d, m.module_id);
          }
        });
      });
    });
  }

  setTypeList() {
    let typeList: Array<string> = [];
    this.deviceService
      .getDevicesV2()
      .then((deviceList) => {
        deviceList.devices.forEach((device) => {
          if (device.device_type !== undefined && device.device_type !== '') {
            typeList.push(device.device_type);
          }
        });
      })
      .finally(() => {
        typeList = typeList.filter(
          (element, index) => index === typeList.indexOf(element),
        );
        this.deviceTypeList$.next(typeList);
      });
  }

  getTypeList(): Observable<Array<string>> {
    return this.deviceTypeList$;
  }
}
