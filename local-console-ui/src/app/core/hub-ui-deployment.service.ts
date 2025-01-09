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
import { HubUIDeviceService } from './hub-ui-device.service';
import { BehaviorSubject, Observable } from 'rxjs';
import { DeployConfigApplyIn, DeployConfigsIn } from './deployment/deployment';
import { DeploymentService } from './deployment/deployment.service';
import { DeviceService } from './device/device.service';

export interface DeploymentConfig {
  config_id: string;
  description?: string;
  models?: { model_id: string; model_version_number: string }[];
  edge_system_sw_package?: { firmware_id: string };
  edge_apps?: { name: string; version: string }[];
}

@Injectable({
  providedIn: 'root',
})
export class HubUiDeploymentService {
  dialogSelectDevices: string[] = [];
  configEdit$ = new BehaviorSubject<boolean>(true);
  deployId = '';
  displayStatus$ = new BehaviorSubject<string>('');
  // Observable
  private disconnectedDevices$ = new BehaviorSubject<string[]>([]);
  private deployingDevices$ = new BehaviorSubject<string[]>([]);
  private failDevices$ = new BehaviorSubject<string[]>([]);
  private successDevices$ = new BehaviorSubject<string[]>([]);
  constructor(
    private deviceService: DeviceService,
    private deploymentsService: DeploymentService,
    private hubUIDeviceService: HubUIDeviceService,
  ) {
    this.hubUIDeviceService
      .getDialogSelectedDevices()
      .subscribe((devices: string[]) => {
        this.dialogSelectDevices = devices;
      });
  }

  getDisconnectedDevices(): Observable<string[]> {
    return this.disconnectedDevices$.asObservable();
  }

  updateDisconnectedDevices(devices: string[]) {
    this.disconnectedDevices$.next(devices);
  }

  getDeployingDevices(): Observable<string[]> {
    return this.deployingDevices$.asObservable();
  }

  updateDeployingDevices(devices: string[]) {
    this.deployingDevices$.next(devices);
  }

  getFailDevices(): Observable<string[]> {
    return this.failDevices$.asObservable();
  }

  updateFailDevices(devices: string[]) {
    this.failDevices$.next(devices);
  }

  getSuccessDevices(): Observable<string[]> {
    return this.successDevices$.asObservable();
  }

  updateSuccessDevices(devices: string[]) {
    this.successDevices$.next(devices);
  }

  startDeploy(config: DeploymentConfig) {
    // Stage 1; create deploy configuration
    let configPayload: DeployConfigsIn = {
      config_id: config.config_id,
    };

    if (config.description) {
      configPayload = {
        ...configPayload,
        description: config.description,
      };
    }

    if (config.models && config.models.length) {
      configPayload = {
        ...configPayload,
        models: [
          {
            model_id: config.models[0].model_id,
            model_version_number: config.models[0].model_version_number,
          },
        ],
      };
    }

    if (config.edge_apps && config.edge_apps.length) {
      configPayload = {
        ...configPayload,
        edge_apps: [
          {
            app_name: config.edge_apps[0].name,
            app_version: config.edge_apps[0].version,
          },
        ],
      };
    }

    if (config.edge_system_sw_package) {
      configPayload = {
        ...configPayload,
        edge_system_sw_package: {
          firmware_id: config.edge_system_sw_package.firmware_id,
        },
      };
    }
    this.deploymentsService
      .createDeploymentConfigV2(configPayload)
      .then((resp) => {
        // stage 2: deploy config
        const deployPayload: DeployConfigApplyIn = {
          device_ids: this.dialogSelectDevices,
        };
        this.deploymentsService
          .deployByConfigurationV2(config.config_id, deployPayload)
          .then((resp) => {
            this.deployId = resp.deploy_id;
          });
      });
  }

  async getDeployStatus() {
    if (
      this.dialogSelectDevices === undefined ||
      (this.dialogSelectDevices as string[]).length < 1 ||
      this.deployId.length < 1
    ) {
      return;
    }

    let successDevices: string[] = [];
    let failDevices: string[] = [];
    let deployingDevices: string[] = [];
    let res: any[] = [];
    this.deploymentsService
      .getDeployStatusV2(this.deployId)
      .then((status) => {
        res = status.devices;
        status.devices.map((d) => {
          let device_id = d.device_id as string;
          switch (d.deploy_status) {
            case 'success':
              successDevices.push(device_id);
              break;
            case 'deploying':
              deployingDevices.push(device_id);
              break;
            case 'fail':
              failDevices.push(device_id);
          }
        });
      })
      .finally(() => {
        this.updateSuccessDevices(successDevices);
        this.updateFailDevices(failDevices);
        let disconnectDevices: string[] = [];
        if (deployingDevices.length == 0) {
          this.updateDeployingDevices([]);
          this.updateDisconnectedDevices([]);
          return;
        }
        this.deviceService
          .getDevicesV2(deployingDevices)
          .then((data) => {
            data.devices.forEach((device) => {
              if (device.connection_state === 'Disconnected') {
                deployingDevices = deployingDevices.filter(
                  (d) => d !== device.device_id,
                );
                disconnectDevices.push(device.device_id);
              }
            });
          })
          .finally(() => {
            this.updateDeployingDevices(deployingDevices);
            this.updateDisconnectedDevices(disconnectDevices);
          });
      });
  }

  setDisplayStatus() {
    this.getDeployStatus();
    this.displayStatus$.next('');
  }

  getDisplayStatus(): Observable<string> {
    return this.displayStatus$.asObservable();
  }

  setConfigEdit(status: boolean) {
    this.configEdit$.next(status);
  }

  getConfigEdit(): Observable<boolean> {
    return this.configEdit$.asObservable();
  }
}
