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

import { Express } from 'express';
import { STREAMING_IMAGES } from '../images';
import { Store } from '../store';

export function registerInferenceControllers(app: Express, data: Store) {
  function getMockInferencesForDevice(deviceId: string) {
    const opMode = data.configurations[deviceId].vapp_type || 'classification';
    if (opMode === 'detection' || opMode === 'generic_detection') {
      //128×96
      return [
        {
          class_id: 0,
          bounding_box_type: 'BoundingBox2d',
          bounding_box: {
            left: 4,
            top: 13,
            right: 90,
            bottom: 70,
          },
          score: 0.914062,
        },
        {
          class_id: 0,
          bounding_box_type: 'BoundingBox2d',
          bounding_box: {
            left: 35,
            top: 35,
            right: 60,
            bottom: 60,
          },
          score: 0.8,
        },
      ];
    } else {
      return [
        { class_id: 2, score: Math.random() * 0.3 + 0.7 },
        { class_id: 1, score: Math.random() * 0.3 + 0.4 },
        { class_id: 3, score: Math.random() * 0.3 + 0.1 },
      ];
    }
  }

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
                T: getFormattedTimestamp(),
                O: 'DAAAAAAABgAKAAQABgAAAAwAAAAAAAYACAAEAAYAAAAEAAAAAgAAABwAAAAEAAAA9P///wEAAAAAAOA8CAAMAAQACAAIAAAAAgAAAAAAdT8=',
              },
            ],
          },
        },
      ],
    }),
  );

  let id = 1;
  app.get('/inferenceresults/devices/:deviceId/withimage', (req, res) => {
    id += 1;
    return res.json({
      data: [
        {
          id: `${id}`,
          inference: {
            id: `${id}.txt`,
            model_id: '0314150123480100',
            model_version_id: '',
            inference_result: {
              DeviceID: 'Aid-00010001-0000-2000-9002-0000000001d1',
              ModelID: '0314150123480100',
              Image: true,
              Inferences: [
                {
                  T: `${id}`,
                  O: getMockInferencesForDevice(req.params.deviceId),
                  F: 1,
                },
              ],
            },
          },
          image: {
            name: `${id}.jpg`,
            sas_url: `/images/devices/1883/image/${id}.jpg`,
          },
        },
      ],
      continuation_token: `${id}`,
    });
  });

  app.get('/inferenceresults/devices/:deviceId/json', (req, res) => {
    if (req.params.deviceId === data.devices.devices[2].device_id) {
      //128×96
      return res.json({
        perception: {
          object_detection_list: [1, 2, 3, 4, 5, 6].map((i) => {
            const left = Math.round(Math.random() * 0.4 * 128 + 0.2 * 128);
            const top = Math.round(Math.random() * 0.4 * 96 + 0.2 * 96);
            const right =
              Math.round(Math.random() * (128 - left - 20)) + left + 20;
            const bottom =
              Math.round(Math.random() * (96 - top - 20)) + top + 20;
            return {
              class_id: i,
              bounding_box_type: 'BoundingBox2d',
              bounding_box: { left, top, right, bottom },
              score: Math.random() * 0.3 + 0.7,
            };
          }),
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
    data.streaming_image_index[req.params.deviceId] =
      ((data.streaming_image_index[req.params.deviceId] || 0) + 1) %
      STREAMING_IMAGES.length;
    return res.send(
      Buffer.from(
        STREAMING_IMAGES[data.streaming_image_index[req.params.deviceId]],
        'base64',
      ),
    );
  });
}

function getFormattedTimestamp() {
  const now = new Date();

  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');
  const milliseconds = String(now.getMilliseconds()).padStart(3, '0');

  return `${year}${month}${day}${hours}${minutes}${seconds}${milliseconds}`;
}
