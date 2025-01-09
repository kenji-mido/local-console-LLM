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

import { Injectable, Output } from '@angular/core';
import { CommandService } from '../command/command.service';
import { HttpErrorResponse, HttpParams } from '@angular/common/http';
import { HttpApiClient } from '../common/http/http';
import {
  DEFAULT_ROI,
  DeviceFrame,
  DeviceListV2,
  DeviceV2,
  isLocalDevice,
  LocalDevice,
  ModuleConfigurationV2,
  ROI,
  SENSOR_SIZE,
  UpdateModuleConfigurationPayloadV2,
} from './device';
import { environment } from '../../../environments/environment';
import { ExecuteCommandPayloadV2, InferenceCommand } from '../command/command';
import { ReplaySubject, Subject } from 'rxjs';
import { EdgeAppModuleConfigurationV2 } from '../module/edgeapp';
import { Configuration } from './configuration';
import { Point2D } from '../drawing/drawing';
import { Mode } from '../inference/inference';

@Injectable({
  providedIn: 'root',
})
export class DeviceService {
  private __lastKnownROICache = new Map<string, ROI>();
  private devicePathV2 = `${environment.apiV2Url}/devices`;
  private deviceSelectedSubject = new ReplaySubject<DeviceV2>(1);
  private devicesSubject = new ReplaySubject<DeviceV2[]>(1);
  public deviceSelected$ = this.deviceSelectedSubject.asObservable();
  public devices$ = this.devicesSubject.asObservable();

  constructor(
    private commands: CommandService,
    private http: HttpApiClient,
  ) {}

  getPreviewImageV2(
    deviceId: string,
    roiOffset: Point2D = new Point2D(0, 0),
    roiSize: Point2D = SENSOR_SIZE,
  ) {
    const moduleName = '$system';
    const payload: ExecuteCommandPayloadV2 = {
      command_name: 'direct_get_image',
      parameters: {
        sensor_name: 'IMX500',
        CropHOffset: roiOffset.x,
        CropVOffset: roiOffset.y,
        CropHSize: roiSize.x,
        CropVSize: roiSize.y,
      },
    };
    return this.commands.executeCommandV2(deviceId, moduleName, payload);
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

  getDeviceV2(id: string) {
    return this.http.get<DeviceV2>(`${this.devicePathV2}/${id}`);
  }

  async updateDeviceName(device_id: string, device_name: string) {
    const updateResp = await this.http.patch<any>(
      `${this.devicePathV2}/${device_id}?new_name=${device_name}`,
      {},
    );
    return updateResp;
  }

  async updateModuleConfigurationV2(
    device_id: string,
    module_id: string,
    payload: UpdateModuleConfigurationPayloadV2,
  ) {
    const moduleResp = await this.http.patch<ModuleConfigurationV2>(
      `${this.devicePathV2}/${device_id}/modules/${module_id}`,
      payload,
    );
    return moduleResp;
  }

  async stopUploadInferenceResultV2(deviceId: string, edgeAppModuleId: string) {
    return this.uploadInferenceResultV2(
      deviceId,
      edgeAppModuleId,
      InferenceCommand.STOP,
    );
  }

  async uploadInferenceResultV2(
    deviceId: string,
    edgeAppModuleId: string,
    cmd: InferenceCommand,
  ) {
    const payload: UpdateModuleConfigurationPayloadV2 = {
      property: {
        configuration: {},
      },
    };
    await this.getModuleV2(deviceId, edgeAppModuleId).then((data) => {
      let config: EdgeAppModuleConfigurationV2 = data.property
        .configuration as EdgeAppModuleConfigurationV2;
      if (
        !config.edge_app ||
        !config.edge_app.common_settings ||
        !config.edge_app.common_settings.process_state
      ) {
        config = {
          ...config,
          edge_app: {
            ...config.edge_app,
            common_settings: {
              ...config.edge_app?.common_settings,
              process_state: cmd,
            },
          },
        };
      } else {
        config.edge_app.common_settings.process_state = cmd;
      }
      payload.property.configuration = {
        ...config,
      };
    });
    return this.updateModuleConfigurationV2(deviceId, edgeAppModuleId, payload);
  }

  async getModuleV2(device_id: string, module_id: string) {
    const moduleResp = await this.http.get<ModuleConfigurationV2>(
      `${this.devicePathV2}/${device_id}/modules/${module_id}`,
    );
    return moduleResp;
  }

  async deleteDevice(device: LocalDevice) {
    const result = await this.http.delete(
      `${this.devicePathV2}/${device.port}`,
    );
    await this.loadDevices();
    return result;
  }

  async createDevice(device_name: string, mqtt_port: number) {
    var result = {};
    try {
      result = await this.http.post(`${this.devicePathV2}`, {
        device_name,
        mqtt_port,
      });
    } catch (err) {
      console.error('Could not register the device', err);
      return null;
    }
    await this.loadDevices();
    return result;
  }

  async getDeviceNextImage(
    device: LocalDevice,
    roiOffset: Point2D = new Point2D(0, 0),
    roiSize: Point2D = SENSOR_SIZE,
  ): Promise<string> {
    const result = await this.getPreviewImageV2(
      device.port.toString(),
      roiOffset,
      roiSize,
    );
    if (result.result !== 'SUCCESS') {
      throw new Error();
    }
    return `data:image/png;base64,${result.command_response['image']}`;
  }

  setSelectedDevice(device: DeviceV2) {
    if (!!device) this.deviceSelectedSubject.next(device);
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

  getDeviceStream(
    device: LocalDevice,
    roiOffset: Point2D,
    roiSize: Point2D,
    interval: number,
  ) {
    const stream = new Subject<DeviceFrame | Error>();
    let running = true;
    const tick = (async () => {
      let result: DeviceFrame | Error;
      if (!running) return;
      try {
        const image = await this.getDeviceNextImage(device, roiOffset, roiSize);
        result = <DeviceFrame>{
          image,
        };
      } catch (error) {
        result = new Error('Cannot get device frame', error as Error);
      }
      if (running) {
        stream.next(result);
        window.setTimeout(tick, interval);
      }
    }).bind(this);
    tick();
    return {
      stream: stream.asObservable(),
      stopStream: () => {
        stream.complete();
        running = false;
      },
    };
  }

  startUploadInferenceData(
    deviceId: string,
    roiOffset: Point2D,
    roiSize: Point2D,
    mode: Mode,
  ) {
    const moduleName = '$system';
    const payload: ExecuteCommandPayloadV2 = {
      command_name: 'StartUploadInferenceData',
      parameters: {
        CropHOffset: roiOffset.x,
        CropVOffset: roiOffset.y,
        CropHSize: roiSize.x,
        CropVSize: roiSize.y,
        Mode: mode,
      },
    };
    const result = this.commands.executeCommandV2(
      deviceId,
      moduleName,
      payload,
    );
    // If successful
    this.__lastKnownROICache.set(deviceId, {
      offset: roiOffset.clone(),
      size: roiSize.clone(),
    });
    return result;
  }
  stopUploadInferenceData(deviceId: string) {
    const moduleName = '$system';
    const payload: ExecuteCommandPayloadV2 = {
      command_name: 'StopUploadInferenceData',
      parameters: {},
    };
    return this.commands.executeCommandV2(deviceId, moduleName, payload);
  }

  async patchConfiguration(device_id: string, configuration: Configuration) {
    // TODO: handle error
    await this.http.patch(
      `${this.devicePathV2}/${device_id}/configuration`,
      configuration,
    );
  }
  async getConfiguration(device_id: string): Promise<Configuration> {
    // TODO: handle error
    return await this.http.get<Configuration>(
      `${this.devicePathV2}/${device_id}/configuration`,
    );
  }

  private patchLocalDeviceCachedROI(device: DeviceV2) {
    if (isLocalDevice(device)) {
      device.last_known_roi =
        this.__lastKnownROICache.get(device.device_id) || DEFAULT_ROI;
    }
    return device;
  }
}
