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

import { Configuration } from '@app/core/device/configuration';
import { NICS } from '@samplers/nics';
import cors from 'cors';
import express from 'express';
import { DeployHistoriesOutList } from '../src/test/samplers/deployment';
import { DeviceList } from '../src/test/samplers/device';
import { registerDeploymentControllers } from './http/deployment';
import { registerDeviceControllers } from './http/devices';
import { registerInferenceControllers } from './http/inferences';
import { registerNicControllers } from './http/nics';
import { LocalDeployHistories, Store } from './store';
import { registerNotificationsWebSocketController } from './ws/notifications';

export function setupMockServer({
  port = 8000,
  setupHttp = false,
  setupWs = false,
}) {
  const __devices = DeviceList.sample();

  const data: Store = {
    devices: __devices,
    deployments: <LocalDeployHistories>(
      DeployHistoriesOutList.sampleHistories(__devices.devices)
    ),
    streaming_image_index: {},
    configurations: <{ [key: string]: Configuration }>{},
    nics: NICS.sampleList(),
    configPatchReqIds: new Map(
      __devices.devices.map((d) => <[string, string]>[d.device_id, '']),
    ),
  };

  const app = express();
  app.use(express.json());
  app.use(
    cors({
      origin: 'http://localhost:4200',
    }),
  );

  const server = app.listen(port, () => {
    const address = server.address();
    if (address && typeof address !== 'string') {
      const port = address.port;
      console.log(`Server running on localhost:${port}`);
    } else {
      console.error('Failed to get server address');
    }
  });

  app.get('/health', (req, res) => {
    res.status(200).send();
  });

  if (setupHttp) {
    registerDeviceControllers(app, data);
    registerDeploymentControllers(app, data);
    registerInferenceControllers(app, data);
    registerNicControllers(app, data);
  }

  if (setupWs) {
    registerNotificationsWebSocketController(server, app);
  }

  // POST models, firmwares, edge_apps and deploy_configs/apply
  app.post('*', (req, res) => {
    res.json({ result: 'SUCCESS' });
  });

  return {
    app,
    server,
    data,
  };
}

if (require.main === module) {
  setupMockServer({ port: 8000, setupHttp: true, setupWs: true });
}
