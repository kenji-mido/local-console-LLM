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

import fs from 'fs';
import path from 'path';
import express, { Request, Response, NextFunction } from 'express';
import cors from 'cors';
// For some reason @samplers/device WON'T WORK
// with ts-node. But @app is completely fine...
import { Device, DeviceList } from '../src/test/samplers/device';
import { Configurations } from '../src/test/samplers/configuration';
import {
  DeployHistoriesOutList,
  DeployHistory,
  getRandomId,
} from '../src/test/samplers/deployment';
import { DeviceListV2, LocalDevice } from '@app/core/device/device';
import {
  DeployConfigsIn,
  DeployHistoriesOut,
  DeployHistoryOut,
  DeployConfigApplyIn,
  DeployHistoryDevicesOut,
} from '@app/core/deployment/deployment';
import { STREAMING_IMAGES } from './images';
import { Configuration } from '@app/core/device/configuration';

class LocalDeployHistories implements DeployHistoriesOut {
  constructor(
    public deploy_history: DeployHistoryOut[],
    public continuation_token: string | null,
  ) {}
}

class LocalDeviceList implements DeviceListV2 {
  constructor(
    public continuation_token: string,
    public devices: LocalDevice[],
  ) {}
}

const __devices = <LocalDeviceList>DeviceList.sampleLocal();

const data = {
  devices: __devices,
  deployments: <LocalDeployHistories>(
    DeployHistoriesOutList.sampleHistories(__devices.devices)
  ),
  streaming_image_index: 0,
  configurations: <{ [key: string]: Configuration }>{},
};

const app = express();
app.use(express.json());
app.use(
  cors({
    origin: 'http://localhost:4200',
  }),
);

// General-purpose delay middleware generator
const delay =
  (duration: number) => (req: Request, res: Response, next: NextFunction) => {
    setTimeout(next, duration);
  };

app.get('/devices', (req, res) => {
  res.json(data.devices);
});

app.post('/devices', (req, res) => {
  let device_name, mqtt_port;
  ({ device_name, mqtt_port } = req.body);
  data.devices.devices.push(
    Device.sampleLocal(Device.sample(device_name), mqtt_port),
  );
  res.json(data.devices);
});

app.delete('/devices/:devicePort', (req: Request, res: Response) => {
  const devicePort = parseInt(req.params['devicePort'], 10);
  const deviceIndex = data.devices.devices.findIndex(
    (d) => d.port === devicePort,
  );

  if (deviceIndex === -1) {
    res.status(404).send();
  }
  data.devices.devices.splice(deviceIndex, 1);
  res.json(data.devices);
});

app.get('/provisioning/qrcode', (req, res) => {
  const imagePath = path.join(__dirname, 'assets', 'qr_image.png');
  fs.readFile(imagePath, (err, imageData) => {
    if (err) {
      console.error(err);
      res.status(500).send();
      return;
    }
    res.json({
      result: 'SUCCESS',
      contents: imageData.toString('base64'),
      expiration_date: new Date(Date.now() + 1000 * 60 * 60).toISOString(),
    });
  });
});

app.post(
  '/devices/:devicePort/modules/([$])system/command',
  delay(1500),
  (req, res) => {
    data.streaming_image_index =
      (data.streaming_image_index + 1) % STREAMING_IMAGES.length;
    res.json({
      result: 'SUCCESS',
      command_response: {
        result: 'Succeeded',
        image: STREAMING_IMAGES[data.streaming_image_index],
      },
    });
  },
);

app.patch('/devices/:deviceId(\\d+)/configuration', (req, res) => {
  data.configurations[req.params['deviceId']] = req.body;
  return res.json({ result: 'SUCCESS' });
});

app.get('/devices/:deviceId(\\d+)/configuration', (req, res) => {
  data.configurations[req.params['deviceId']] =
    data.configurations[req.params['deviceId']] || Configurations.sample();
  res.json(data.configurations[req.params['deviceId']]);
});

app.get('/inferenceresults/devices/:deviceId(\\d+)', (req, res) =>
  res.json({
    data: [
      {
        id: '20241028085916375.txt',
        model_id: '0311031111110100',
        model_version_id: '',
        inference_result: {
          DeviceID: 'Aid-00010001-0000-2000-9002-0000000001d1',
          ModelID: '0311031111110100',
          Image: true,
          Inferences: [
            {
              T: '20241028085916375',
              O: 'DAAAAAAABgAKAAQABgAAAAwAAAAAAAYACAAEAAYAAAAEAAAAAgAAABwAAAAEAAAA9P///wEAAAAAAOA8CAAMAAQACAAIAAAAAgAAAAAAdT8=',
            },
          ],
        },
      },
    ],
  }),
);

app.get('/inferenceresults/devices/:deviceId/json', (req, res) => {
  if (req.params.deviceId === data.devices.devices[2].device_id) {
    //128×96
    const left = Math.round(Math.random() * 0.4 * 128 + 0.2 * 128);
    const top = Math.round(Math.random() * 0.4 * 96 + 0.2 * 96);
    const right = Math.round(Math.random() * (128 - left - 20)) + left + 20;
    const bottom = Math.round(Math.random() * (96 - top - 20)) + top + 20;
    return res.json({
      perception: {
        object_detection_list: [
          {
            class_id: 0,
            bounding_box_type: 'BoundingBox2d',
            bounding_box: { left, top, right, bottom },
            score: Math.random() * 0.3 + 0.7,
          },
        ],
      },
    });
  }
  return res.json({
    perception: {
      classification_list: [
        { class_id: 2, score: Math.random() * 0.3 + 0.7 },
        { class_id: 1, score: Math.random() * 0.3 + 0.4 },
        { class_id: 3, score: Math.random() * 0.3 + 0.1 },
      ],
    },
  });
});

app.get('/images/devices/:deviceId/image/:timestamp', (req, res) => {
  data.streaming_image_index =
    (data.streaming_image_index + 1) % STREAMING_IMAGES.length;
  return res.send(
    Buffer.from(STREAMING_IMAGES[data.streaming_image_index], 'base64'),
  );
});

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
    (dev) => String(dev.port) == body.device_ids[0],
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

// POST models, firmwares, edge_apps and deploy_configs/apply
app.post('*', (req, res) => {
  res.json({ result: 'SUCCESS' });
});

app.get('/health', (req, res) => {
  res.status(200).send();
});

// Start the server on port 8000
const PORT = 8000;
app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});

//add /files, /model /firmware(2) /edge_app /deploy_config /deploy_
