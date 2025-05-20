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

import { Configurations } from '@samplers/configuration';
import { Device } from '@samplers/device';
import { Express, Request, Response } from 'express';
import fs from 'fs';
import path from 'path';
import { delay } from '../common';
import { STREAMING_IMAGES } from '../images';
import { Store } from '../store';

export function registerDeviceControllers(app: Express, data: Store) {
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

  app.post('/devices/:deviceId/command', delay(1000), (req, res) => {
    data.streaming_image_index[req.params['deviceId']] =
      ((data.streaming_image_index[req.params['deviceId']] || 0) + 1) %
      STREAMING_IMAGES.length;
    res.json({
      result: 'SUCCESS',
      command_response: {
        res_info: { code: 0 },
        image:
          STREAMING_IMAGES[data.streaming_image_index[req.params['deviceId']]],
      },
    });
  });
  app.get('/devices', (req, res) => {
    res.json(data.devices);
  });

  app.get('/devices/:deviceId', (req: Request, res: Response) => {
    const devicePort = req.params['deviceId'];
    const deviceIndex = data.devices.devices.findIndex(
      (d) => d.device_id === devicePort,
    );
    console.log("Here's what I found: ", devicePort, deviceIndex);
    if (deviceIndex === -1) {
      res.status(404).send();
    }
    res.json(data.devices.devices[deviceIndex]);
  });

  app.post('/devices', (req, res) => {
    let device_name, mqtt_port;
    ({ device_name, mqtt_port } = req.body);
    data.devices.devices.push(
      Device.sample({ device_name, device_id: mqtt_port }),
    );
    res.json(data.devices);
  });

  app.delete('/devices/:deviceId', (req: Request, res: Response) => {
    const devicePort = req.params['deviceId'];
    const deviceIndex = data.devices.devices.findIndex(
      (d) => d.device_id === devicePort,
    );

    if (deviceIndex === -1) {
      res.status(404).send();
    }
    data.devices.devices.splice(deviceIndex, 1);
    res.json(data.devices);
  });

  app.patch('/devices/:deviceId(\\d+)/configuration', (req, res) => {
    console.log(req.originalUrl);
    data.configurations[req.params['deviceId']] = req.body;
    return res.json({ result: 'SUCCESS' });
  });

  app.get('/devices/:deviceId(\\d+)/configuration', (req, res) => {
    console.log(req.originalUrl);
    data.configurations[req.params['deviceId']] =
      data.configurations[req.params['deviceId']] || Configurations.sample();
    res.json(data.configurations[req.params['deviceId']]);
  });

  app.patch('/devices/:deviceid(\\d+)/modules/node', (req, res) => {
    console.log(req.originalUrl);
    res.json({ result: 'SUCCESS' });
  });

  app.patch('/devices/:deviceid(\\d+)/modules/node/property', (req, res) => {
    console.log(req.originalUrl);
    const deviceId = req.params['deviceId'];
    data.configPatchReqIds.set(
      deviceId,
      req.body?.configuration?.edge_app?.req_info?.req_id,
    );
    res.status(200).send();
  });

  app.get(
    '/devices/:deviceid(\\d+)/modules/node/property',
    delay(2000),
    (req, res) => {
      console.log(req.originalUrl);
      const deviceId = req.params['deviceId'];
      res.json({
        state: {
          edge_app: {
            res_info: {
              res_id: data.configPatchReqIds.get(deviceId),
            },
          },
        },
      });
    },
  );
}
