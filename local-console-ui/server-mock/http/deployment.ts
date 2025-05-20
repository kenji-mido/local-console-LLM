/**
 * Copyright 2025 Sony Semiconductor Solutions Corp.
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
  DeployConfigApplyIn,
  DeployConfigsIn,
  DeployHistoryDevicesOut,
} from '@app/core/deployment/deployment';
import { DeployHistory, getRandomId } from '@samplers/deployment';
import { Express } from 'express';
import { Store } from '../store';

export function registerDeploymentControllers(app: Express, data: Store) {
  app.post('/files', (req, res) => {
    let file_path, type_code;
    ({ file_path, type_code } = req.body);
    res.json({
      result: 'SUCCESS',
      file_info: {
        file_id: getRandomId(),
        name: file_path,
        type_code: type_code,
        size: 0,
      },
    });
  });

  app.post('/deploy_configs', (req, res) => {
    console.log(req.originalUrl);
    const body: DeployConfigsIn = req.body;
    let edge_app_package_id: string | null = null;
    let model_id: string | null = null;
    let fw_id_1: string | null = null;
    let fw_id_2: string | null = null;

    if (body.edge_apps !== null && body.edge_apps !== undefined) {
      edge_app_package_id = body.edge_apps[0].edge_app_package_id;
    }
    if (body.models !== null && body.models !== undefined) {
      model_id = body.models[0].model_id;
    }
    if (
      body.edge_system_sw_package !== null &&
      body.edge_system_sw_package !== undefined &&
      body.edge_system_sw_package.length > 0
    ) {
      fw_id_1 = body.edge_system_sw_package[0].firmware_id;
      if (body.edge_system_sw_package.length == 2) {
        fw_id_2 = body.edge_system_sw_package[1].firmware_id;
      }
    }
    data.deployments.deploy_history.push(
      DeployHistory.sample(
        body.config_id,
        fw_id_1,
        fw_id_2,
        edge_app_package_id,
        model_id,
      ),
    );

    res.json({ result: 'SUCCESS' });
  });

  app.post('/deploy_configs/:config_id/apply', (req, res) => {
    const body: DeployConfigApplyIn = req.body;
    const selected_device = data.devices.devices.filter(
      (dev) => dev.device_id == body.device_ids[0],
    );
    const device_info: DeployHistoryDevicesOut[] = [
      {
        device_id: body.device_ids[0],
        device_name: selected_device[0].device_name,
      },
    ];

    data.deployments.deploy_history.at(-1)!.devices = device_info;

    res.json({ result: 'SUCCESS' });
  });

  app.get('/deploy_history', (req, res) => {
    res.json(data.deployments);
  });
}
