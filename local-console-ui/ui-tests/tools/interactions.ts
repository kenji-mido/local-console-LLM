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

import { Environment } from '@app/core/common/environment';
import { FileInformation } from '@app/core/file/file-input/file-input.component';
import { FolderInformation } from '@app/core/file/folder-path-input/folder-picker.component';
import { TaskType } from '@app/core/inference/inference';
import { expect, Route, type Locator, type Page } from '@playwright/test';
import { waitForExpect } from '@test/utils';
import { readFileSync } from 'fs';
import { basename, join } from 'path';
import { defer } from './promise';

const SMALLEST_VALID_JPEG =
  '/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=';

export async function createDevice(
  page: Page,
  deviceName: string,
  port: number,
) {
  await page
    .getByTestId('device-register-name')
    .locator('input')
    .fill(deviceName);
  await page
    .getByTestId('device-register-port')
    .locator('input')
    .fill(port.toString());
  await page.getByTestId('device-register').click();

  const env = new Environment();

  await page.waitForResponse(
    (response) =>
      response.url().includes(`${env.getApiUrl()}/devices`) &&
      response.status() === 200,
  );
}

export async function loadFileIntoFileInput(
  page: Page,
  file: string,
  fileInput: Locator,
) {
  const fileName = file.split('/').pop() || 'invalid_file_name';

  const filePath = join(__dirname, file);
  const payload = Object.values(readFileSync(filePath));
  await page.evaluate(
    (args: any[]) => {
      // Mock electron
      const electron = window as any;
      electron.appBridge = { isElectron: true };
      electron.appBridge.selectFile = () => {
        window.appBridge = undefined; // restore window object
        return Promise.resolve(<FileInformation>{
          basename: args[0],
          path: args[1],
          data: new Uint8Array(args[2]),
        });
      };
    },
    [basename(file), filePath, payload],
  );
  await fileInput.getByTestId('actuator').click();

  await expect(
    fileInput.getByTestId('filename').getByTestId('text'),
  ).toContainText(fileName);
}

export async function loadFolderIntoFolderInput(
  page: Page,
  folder: string,
  folderInput: Locator,
) {
  await page.evaluate(
    (args: any[]) => {
      // Mock electron
      const electron = window as any;
      electron.appBridge = { isElectron: true };
      electron.appBridge.selectFolder = () => {
        window.appBridge = undefined; // restore window object
        return Promise.resolve(<FolderInformation>{
          path: args[0],
        });
      };
    },
    [folder],
  );
  await folderInput.getByTestId('actuator').click();

  await expect(
    folderInput.getByTestId('folder').getByTestId('text'),
  ).toContainText(folder);
}

export async function setInferenceRouteInterceptors(
  page: Page,
  correctFormat = true,
  jsonFormatInference: {}[] | string | undefined = undefined,
  isJsonFormat: 0 | 1 = 1,
  taskType: TaskType | undefined = TaskType.ObjectDetection,
) {
  await page.route(`**/devices/1884/command`, async (route: Route, request) => {
    await route.fulfill({ json: { result: 'SUCCESS' } });
  });
  const signals = {
    isInferenceListCalled: defer(),
    isInferenceToJsonCalled: defer(),
  };

  await page.route(
    `**/inferenceresults/devices/1884/withimage?limit=1`,
    async (route: Route, request) => {
      const identifier = Date.now().toString();
      signals.isInferenceListCalled.resolve(true);

      let inference: [{}];
      if (jsonFormatInference) {
        inference = [
          {
            T: identifier,
            O: jsonFormatInference,
            F: isJsonFormat,
            P: taskType,
          },
        ];
      } else {
        inference = [
          {
            T: identifier,
            O: 'FIX_STRING',
          },
        ];
      }

      await route.fulfill({
        json: {
          data: [
            {
              id: identifier,
              inference: {
                id: identifier + '.txt',
                model_id: '0308000000000100',
                model_version_id: '',
                inference_result: {
                  DeviceID: 'sid-100A50500A2010072664012000000000',
                  ModelID: '0308000000000100',
                  Image: true,
                  Inferences: inference,
                },
              },
              image: {
                name: identifier + '.jpg',
                sas_url: identifier + '.jpg',
              },
            },
          ],
          continuation_token: identifier,
        },
      });
    },
  );
  if (correctFormat) {
    await page.route(
      `**/inferenceresults/devices/1884/json?flatbuffer_payload=FIX_STRING`,
      async (route: Route, request) => {
        signals.isInferenceToJsonCalled.resolve(true);
        await route.fulfill({
          json: {
            perception: {
              object_detection_list: [
                {
                  class_id: 3,
                  bounding_box_type: 'BoundingBox2d',
                  bounding_box: { left: 0, top: 0, right: 100, bottom: 100 },
                  score: 0,
                },
                {
                  class_id: 1,
                  bounding_box_type: 'BoundingBox2d',
                  bounding_box: { left: 0, top: 0, right: 100, bottom: 100 },
                  score: 0,
                },
                {
                  class_id: 4,
                  bounding_box_type: 'BoundingBox2d',
                  bounding_box: { left: 0, top: 0, right: 100, bottom: 100 },
                  score: 0,
                },
                {
                  class_id: 0,
                  bounding_box_type: 'BoundingBox2d',
                  bounding_box: { left: 0, top: 0, right: 100, bottom: 100 },
                  score: 0,
                },
                {
                  class_id: 2,
                  bounding_box_type: 'BoundingBox2d',
                  bounding_box: { left: 0, top: 0, right: 100, bottom: 100 },
                  score: 0,
                },
              ],
            },
          },
        });
      },
    );
  } else {
    if (jsonFormatInference) {
      await page.route(
        `**/inferenceresults/devices/1884/json?flatbuffer_payload=%5Bobject%20Object%5D,%5Bobject%20Object%5D`,
        async (route) => {
          await route.fulfill({
            status: 404,
            json: {
              result: 'ERROR',
              message: 'Device schema not configured',
              code: '001002',
            },
          });
        },
      );
    } else {
      await page.route(
        `**/inferenceresults/devices/1884/json?flatbuffer_payload=FIX_STRING`,
        async (route: Route, request) => {
          signals.isInferenceToJsonCalled.resolve(true);
          await route.fulfill({
            json: {
              perception: {
                object_detection_list: [
                  {
                    class_id: 3,
                    bounding_box_type: 'WRONG',
                  },
                ],
              },
            },
          });
        },
      );
    }
  }
  await page.route('**/image/*', (route) => {
    const buffer = Buffer.from(SMALLEST_VALID_JPEG, 'base64');
    route.fulfill({
      status: 200,
      contentType: 'image/jpeg',
      body: buffer,
    });
  });
  return signals;
}

export async function selectDefaultDevice(page: Page) {
  // Find the target device
  await page.getByTestId('device-selector-btn').click();

  const status = await page
    .getByTestId('device-selector-status-0')
    .getByTestId('text')
    .innerText();
  await waitForExpect(() => expect(status).toBe('Connected')); // matching is case and space sensitive

  // Select the target device
  await page.getByTestId('device-selector-option-0').check();
  await page
    .locator('app-device-selector-popup')
    .locator('button', { hasText: 'Select' })
    .click();
  await expect(page.getByTestId('selected-device')).toContainText('Default');
  await expect(page.locator('app-device-selector-popup')).not.toBeVisible();
}
