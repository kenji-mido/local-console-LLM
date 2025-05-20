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
  DeployHistoriesOut,
  DeployHistoryDevicesOut,
  DeployHistoryEdgeAppsOut,
  DeployHistoryEdgeSystemOut,
  DeployHistoryModelsOut,
  DeployHistoryOut,
  DeploymentStatusOut,
} from '@app/core/deployment/deployment';
import { LocalDevice } from '@app/core/device/device';
import { Device } from '@samplers/device';

export function getRandomId(): string {
  return Math.floor(Math.random() * 10 ** 20).toString();
}

function getRandomDeploymentStatus(): DeploymentStatusOut {
  const values = Object.values(DeploymentStatusOut);
  const randomIndex = Math.floor(Math.random() * values.length);
  return values[randomIndex];
}

export module DeployHistoriesOutList {
  export function sampleHistories(devices?: LocalDevice[]) {
    return <DeployHistoriesOut>{
      continuation_token: '',
      deploy_history: sampleHistoryList(devices),
    };
  }

  export function sampleHistoryList(
    devices?: LocalDevice[],
  ): DeployHistoryOut[] {
    devices ||= [Device.sample()];
    return devices.map((device, index) => {
      const id = index + '';
      return <DeployHistoryOut>{
        deploy_id: id,
        config_id: id,
        from_datetime: new Date().toISOString(),
        deploy_type: '',
        deploying_cnt: 0,
        success_cnt: 0,
        fail_cnt: 0,
        devices: [device],
        models: [HistoryModel.sampleModel(getRandomId())],
      };
    });
  }

  export function sampleEmpty(): DeployHistoriesOut {
    return {
      continuation_token: '',
      deploy_history: [],
    };
  }
}

export module DeployHistory {
  export function sample(
    config_id: string | undefined,
    firmware_id_1: string | null,
    firmware_id_2: string | null,
    edge_app_package_id: string | null,
    model_id: string | null,
  ): DeployHistoryOut {
    const edge_system_sw_package: DeployHistoryEdgeSystemOut[] = [];
    const models: DeployHistoryModelsOut[] = [];
    const edge_apps: DeployHistoryEdgeAppsOut[] = [];

    if (firmware_id_1 !== null) {
      edge_system_sw_package.push(
        HistoryEdgeSystem.sampleEdgeSystem(firmware_id_1),
      );
    }
    if (firmware_id_2 !== null) {
      edge_system_sw_package.push(
        HistoryEdgeSystem.sampleEdgeSystem(firmware_id_2),
      );
    }
    if (edge_app_package_id !== null) {
      edge_apps.push(HistoryEdgeApps.sampleEdgeApp(edge_app_package_id));
    }
    if (model_id !== null) {
      models.push(HistoryModel.sampleModel(model_id));
    }

    if (config_id === undefined) {
      config_id = getRandomId();
    }
    return {
      deploy_id: getRandomId(),
      config_id: config_id,
      from_datetime: new Date().toISOString(),
      deploy_type: '',
      deploying_cnt: 0,
      success_cnt: 0,
      fail_cnt: 0,
      edge_system_sw_package: edge_system_sw_package,
      models: models,
      edge_apps: edge_apps,
      devices: HistoryDevices.sampleModel(),
    };
  }
}

export module HistoryEdgeSystem {
  export function sampleEdgeSystem(
    firmware_id: string,
  ): DeployHistoryEdgeSystemOut {
    return {
      firmware_id: firmware_id,
      firmware_version: '1.0.0',
      status: getRandomDeploymentStatus(),
    };
  }
}

export module HistoryModel {
  export function sampleModel(model_id: string): DeployHistoryModelsOut {
    return {
      model_id: model_id,
      status: getRandomDeploymentStatus(),
    };
  }
}

export module HistoryEdgeApps {
  export function sampleEdgeApp(edge_app_id: string): DeployHistoryEdgeAppsOut {
    return {
      app_name: edge_app_id,
      app_version: '0.0.1',
      description: 'description',
      status: getRandomDeploymentStatus(),
    };
  }
}

export module HistoryDevices {
  export function sampleModel(): DeployHistoryDevicesOut[] {
    return [
      {
        device_id: getRandomId(),
        device_name: getRandomId(),
      },
    ];
  }
}
