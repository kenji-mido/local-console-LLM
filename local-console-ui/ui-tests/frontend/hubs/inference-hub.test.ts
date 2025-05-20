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
import { DeviceListV2 } from '@app/core/device/device';
import { Detection, TaskType } from '@app/core/inference/inference';
import { expect, Page, Route } from '@playwright/test';
import { DeviceList } from '@samplers/device';
import { waitForExpect } from '@test/utils';
import {
  loadFileIntoFileInput,
  loadFolderIntoFolderInput,
  setInferenceRouteInterceptors,
} from '../../tools/interactions';
import { test } from './../fixtures/fixtures';

const setupRoutes = async (
  page: Page,
  configuration: Configuration,
  deviceList: DeviceListV2,
): Promise<void> => {
  await page.route('**/health', async (route: Route) => {
    await route.fulfill();
  });
  await page.route('**/devices?limit=500', async (route: Route) => {
    await route.fulfill({ json: deviceList });
  });

  await page.route(
    `**/devices/${deviceList.devices[0].device_id}/configuration**`,
    async (route: Route, request) => {
      if (request.method() === 'GET') {
        // Mock device configuration
        await route.fulfill({ json: configuration });
      } else if (request.method() === 'PATCH') {
        await route.fulfill({ json: configuration });
      }
    },
  );

  let lastReqId: string;
  await page.route(
    `**/devices/1884/modules/node/property`,
    async (route: Route, request) => {
      const method = request.method();
      if (method === 'PATCH') {
        const body = request.postDataJSON();
        if (body.configuration.edge_app) {
          lastReqId = body.configuration.edge_app.req_info.req_id;
        }
        await route.fulfill();
      } else if (method === 'GET') {
        await route.fulfill({
          json: {
            state: {
              edge_app: {
                res_info: {
                  res_id: lastReqId,
                },
              },
            },
          },
        });
      }
    },
  );
};

const navigateToInferenceHubAndSelectDevice = async (
  page: Page,
): Promise<void> => {
  await page.goto('http://localhost:4200/');
  await page.getByRole('link', { name: 'Inference' }).click();

  // Select a device
  await page.getByTestId('device-selector-btn').click();
  await page.getByTestId('device-selector-option-0').click();
  await page.getByRole('button', { name: 'Select' }).click();

  await page.getByTestId('ai-model-type-selector').click();
  await page
    .locator('mat-option', { hasText: 'Brain Builder Classifier' })
    .click();
};

test.describe(
  'Inference Hub',
  {
    annotation: {
      type: 'Inference Hub',
      description:
        'This test suit covers the FrontEnd tests involving the Data Hub tab',
    },
  },
  () => {
    test.describe(
      'Happy paths',
      {
        annotation: {
          type: 'Happy paths',
          description:
            'These tests showcase normal operation, when usage is correct, leading to successful outcomes',
        },
      },
      () => {
        let configuration: Configuration;

        const deviceList = DeviceList.sample();

        test.beforeEach(() => {
          configuration = {
            device_dir_path: '/tmp/local-console/inferences',
            size: 100,
            vapp_type: 'classification',
            auto_deletion: false,
          };
        });

        // @ACC_PFREQ-1646.1
        // @ACC_PFREQ-1646.2
        test('When no changes are made to Storage settings, there is no confirmation prompt.', async ({
          page,
        }) => {
          await setupRoutes(page, configuration, deviceList);
          await navigateToInferenceHubAndSelectDevice(page);

          await loadFileIntoFileInput(
            page,
            'samples/configuration_class.json',
            page.getByTestId('ppl-file-select-btn'),
          );

          let requestedConfig = {};
          await page.route(
            `**/devices/${deviceList.devices[0].device_id}/configuration**`,
            async (route: Route, request) => {
              if (request.method() === 'GET') {
                await route.fulfill({ json: configuration });
              } else if (request.method() === 'PATCH') {
                requestedConfig = request.postDataJSON();
                await route.fulfill({ json: configuration });
              } else {
                // Fail the test for unsupported methods
                throw new Error(`Unexpected HTTP method: ${request.method()}`);
              }
            },
          );

          await page.getByTestId('apply-configuration').click();
          await expect(page.getByText('Configuration Applied')).toBeVisible();
          await expect(configuration).toEqual(requestedConfig);
        });

        test(
          'When storage size increases, there is no confirmation prompt.',
          {
            annotation: {
              type: 'When storage size increases, there is no confirmation prompt.',
              description:
                'If the only change in configuration is the storage size limit increase, when clicking "Apply", it should not open any confirmation dialogue.',
            },
          },
          async ({ page }) => {
            await setupRoutes(page, configuration, deviceList);
            await navigateToInferenceHubAndSelectDevice(page);

            await loadFileIntoFileInput(
              page,
              'samples/configuration_class.json',
              page.getByTestId('ppl-file-select-btn'),
            );

            // Increase storage size limit
            await page
              .locator('app-number-spinner')
              .getByRole('button')
              .nth(1)
              .click({ clickCount: 10 });

            let requestedConfig = {};
            await page.route(
              `**/devices/${deviceList.devices[0].device_id}/configuration**`,
              async (route: Route, request) => {
                requestedConfig = request.postDataJSON();
                await route.fulfill({ json: configuration });
              },
            );

            await page.getByTestId('apply-configuration').click();
            await expect(page.getByText('Configuration Applied')).toBeVisible();

            configuration.size = 100 + 10;
            await expect(configuration).toEqual(requestedConfig);
          },
        );

        // @ACC_PFREQ-1511.1
        test(
          'Given User has selected a device in Inference hub and mode is not "Image capture", ' +
            'When "PPL parameter file" configuration is missing, ' +
            '"Apply" and "Start" button are  disabled.',
          async ({ page }) => {
            await setupRoutes(page, configuration, deviceList);
            await navigateToInferenceHubAndSelectDevice(page);

            // Select a device
            await page.getByTestId('device-selector-btn').click();
            await page.getByTestId('device-selector-option-0').click();
            await page.getByRole('button', { name: 'Select' }).click();

            await expect(
              page.getByTestId('apply-configuration'),
            ).toBeDisabled();
            await expect(
              page.getByTestId('start-inference-btn'),
            ).toBeDisabled();
            await expect(page.getByTestId('stop-inference-btn')).toBeDisabled();
          },
        );

        // @ACC_PFREQ-1511.2
        test(
          'Given User has selected a device in Inference hub and mode is not "Image capture", ' +
            'When "PPL parameter file" exists and not changed by the user, ' +
            '"Apply" button is disabled and "Start" button is enabled.',
          async ({ page }) => {
            await setupRoutes(page, configuration, deviceList);
            await navigateToInferenceHubAndSelectDevice(page);

            await loadFileIntoFileInput(
              page,
              'samples/configuration_class.json',
              page.getByTestId('ppl-file-select-btn'),
            );

            // Apply PPL parameter
            await expect(page.getByTestId('apply-configuration')).toBeEnabled();
            await page.getByTestId('apply-configuration').click();

            // Select the same PPL parameter
            await loadFileIntoFileInput(
              page,
              'samples/configuration_class.json',
              page.getByTestId('ppl-file-select-btn'),
            );

            await expect(
              page.getByTestId('apply-configuration'),
            ).toBeDisabled();
            await expect(page.getByTestId('start-inference-btn')).toBeEnabled();
            await expect(page.getByTestId('stop-inference-btn')).toBeDisabled();
          },
        );

        // @ACC_PFREQ-1511.3
        test(
          'Given User has selected a device in Inference hub and mode is not "Image capture", ' +
            'When "PPL parameter file" exists and is changed by the user and inference is stopped, ' +
            '"Apply" button is enabled and "Start" button is disabled.',
          async ({ page }) => {
            await setupRoutes(page, configuration, deviceList);
            await navigateToInferenceHubAndSelectDevice(page);

            await loadFileIntoFileInput(
              page,
              'samples/configuration_class.json',
              page.getByTestId('ppl-file-select-btn'),
            );

            // Apply PPL parameter
            await expect(page.getByTestId('apply-configuration')).toBeEnabled();
            await page.getByTestId('apply-configuration').click();

            // Select a different PPL parameter
            await loadFileIntoFileInput(
              page,
              'samples/configuration_det.json',
              page.getByTestId('ppl-file-select-btn'),
            );

            await expect(page.getByTestId('apply-configuration')).toBeEnabled();
            await expect(
              page.getByTestId('start-inference-btn'),
            ).toBeDisabled();
            await expect(page.getByTestId('stop-inference-btn')).toBeDisabled();
          },
        );

        // @ACC_PFREQ-1511.4
        test(
          'Given User has selected a device in Inference hub and mode is not "Image capture", ' +
            'When "PPL parameter file" is changed by the user and user has applied the change, ' +
            '"Apply" button turns to disabled and "Start" button is enabled .',
          async ({ page }) => {
            await setupRoutes(page, configuration, deviceList);
            await navigateToInferenceHubAndSelectDevice(page);

            await loadFileIntoFileInput(
              page,
              'samples/configuration_class.json',
              page.getByTestId('ppl-file-select-btn'),
            );

            // Apply PPL parameter
            await expect(page.getByTestId('apply-configuration')).toBeEnabled();
            await page.getByTestId('apply-configuration').click();

            await expect(
              page.getByTestId('apply-configuration'),
            ).toBeDisabled();
            await expect(page.getByTestId('start-inference-btn')).toBeEnabled();
            await expect(page.getByTestId('stop-inference-btn')).toBeDisabled();
          },
        );

        // @ACC_PFREQ-1511.5
        test('Should disable all configuration options while the device is streaming', async ({
          page,
        }) => {
          await setupRoutes(page, configuration, deviceList);
          await navigateToInferenceHubAndSelectDevice(page);
          await setInferenceRouteInterceptors(page);
          await page.getByTestId('ai-model-type-selector').click();
          await page
            .locator('mat-option', { hasText: 'Brain Builder Detector' })
            .click();

          await loadFileIntoFileInput(
            page,
            'samples/configuration_class.json',
            page.getByTestId('ppl-file-select-btn'),
          );

          // apply PPL parameter
          await expect(page.getByTestId('apply-configuration')).toBeEnabled();
          await page.getByTestId('apply-configuration').click();

          await expect(page.getByTestId('start-inference-btn')).toBeEnabled();
          await page.getByTestId('start-inference-btn').click();

          await expect(
            page.getByTestId('ai-model-type-selector'),
          ).toBeDisabled();
          await expect(
            page.getByTestId('label-file-select-btn'),
          ).toBeDisabled();
          await expect(page.getByTestId('ppl-file-select-btn')).toBeDisabled();
          await expect(
            page.getByTestId('destination-folder-selector'),
          ).toBeDisabled();
          await expect(page.getByTestId('quota-spinner')).toBeDisabled();
          await expect(
            page.getByTestId('auto-deletion-selector'),
          ).toBeDisabled();
        });

        test('Should prompt user when attempting to enable Automatic File Deletion', async ({
          page,
        }) => {
          // Given
          await setupRoutes(page, configuration, deviceList);
          await navigateToInferenceHubAndSelectDevice(page);

          // When
          await page
            .getByTestId('auto-deletion-selector')
            .getByTestId('option-0')
            .click();

          // Then
          await expect(
            page.getByText(
              'Are you sure you want to enable Automatic File Deletion',
            ),
          ).toBeVisible();
        });

        // @ACC_PFREQ-1646.4
        test('Should keep Automatic File Deletion disabled if prompt is rolled back', async ({
          page,
        }) => {
          // Given
          await setupRoutes(page, configuration, deviceList);
          await navigateToInferenceHubAndSelectDevice(page);

          // When
          await page
            .getByTestId('auto-deletion-selector')
            .getByTestId('option-0')
            .click();
          await page.getByRole('button', { name: 'Keep it disabled' }).click();

          // Then
          await expect(
            page.getByText(
              'Are you sure you want to enable Automatic File Deletion',
            ),
          ).not.toBeVisible();
          await expect(
            page.getByTestId('auto-deletion-selector').getByTestId('option-0'),
          ).toHaveClass(/weak-hub-btn/);
          await expect(
            page.getByTestId('auto-deletion-selector').getByTestId('option-1'),
          ).toHaveClass(/normal-hub-btn/);
        });

        // @ACC_PFREQ-1646.3
        test('Should enable Automatic File Deletion if prompt is accepted', async ({
          page,
        }) => {
          // Given
          await setupRoutes(page, configuration, deviceList);
          await navigateToInferenceHubAndSelectDevice(page);

          // When
          await page
            .getByTestId('auto-deletion-selector')
            .getByTestId('option-0')
            .click();
          await page.getByRole('button', { name: 'Enable' }).click();

          // Then
          await expect(
            page.getByText(
              'Are you sure you want to enable Automatic File Deletion',
            ),
          ).not.toBeVisible();
          await expect(
            page.getByTestId('auto-deletion-selector').getByTestId('option-0'),
          ).toHaveClass(/normal-hub-btn/);
          await expect(
            page.getByTestId('auto-deletion-selector').getByTestId('option-1'),
          ).toHaveClass(/weak-hub-btn/);
        });

        // @ACC_PFREQ-1646.6
        test(
          'Given Automatic File Deletion is enabled, ' +
            'When User changes quota size, ' +
            'Then warning hint is shown.',
          async ({ page }) => {
            // Given
            await setupRoutes(page, configuration, deviceList);
            await navigateToInferenceHubAndSelectDevice(page);

            await loadFileIntoFileInput(
              page,
              'samples/configuration_class.json',
              page.getByTestId('ppl-file-select-btn'),
            );

            await page
              .getByTestId('auto-deletion-selector')
              .getByTestId('option-0')
              .click();
            await page.getByRole('button', { name: 'Enable' }).click();

            await expect(
              page
                .getByTestId('auto-deletion-selector')
                .getByTestId('option-1'),
            ).toHaveClass(/weak-hub-btn/);
            await expect(
              page
                .getByTestId('auto-deletion-selector')
                .getByTestId('option-0'),
            ).toHaveClass(/normal-hub-btn/);

            await expect(
              page.getByText('Default to "Off" on setting change'),
            ).not.toBeVisible();

            await expect(page.getByTestId('apply-configuration')).toBeEnabled();
            await page.getByTestId('apply-configuration').click();

            // When
            await page
              .locator('app-number-spinner')
              .getByRole('button')
              .nth(1)
              .click({ clickCount: 10 });

            // Then
            await expect(
              page
                .getByTestId('auto-deletion-selector')
                .getByTestId('option-0'),
            ).toHaveClass(/weak-hub-btn/);
            await expect(
              page
                .getByTestId('auto-deletion-selector')
                .getByTestId('option-1'),
            ).toHaveClass(/normal-hub-btn/);

            await expect(
              page.getByText('Default to "Off" on setting change'),
            ).toBeVisible();

            await expect(page.getByTestId('apply-configuration')).toBeEnabled();
            await page.getByTestId('apply-configuration').click();

            await expect(
              page.getByText('Default to "Off" on setting change'),
            ).not.toBeVisible();
          },
        );

        // @ACC_PFREQ-1646.5
        test(
          'Given Automatic File Deletion is enabled, ' +
            'When User changes destination folder, ' +
            'Then warning hint is shown.',
          async ({ page }) => {
            // Given
            await setupRoutes(page, configuration, deviceList);
            await navigateToInferenceHubAndSelectDevice(page);

            await loadFileIntoFileInput(
              page,
              'samples/configuration_class.json',
              page.getByTestId('ppl-file-select-btn'),
            );

            await page
              .getByTestId('auto-deletion-selector')
              .getByTestId('option-0')
              .click();
            await page.getByRole('button', { name: 'Enable' }).click();

            await expect(
              page
                .getByTestId('auto-deletion-selector')
                .getByTestId('option-1'),
            ).toHaveClass(/weak-hub-btn/);
            await expect(
              page
                .getByTestId('auto-deletion-selector')
                .getByTestId('option-0'),
            ).toHaveClass(/normal-hub-btn/);

            await expect(
              page.getByText('Default to "Off" on setting change'),
            ).not.toBeVisible();

            await expect(page.getByTestId('apply-configuration')).toBeEnabled();
            await page.getByTestId('apply-configuration').click();

            // When
            await loadFolderIntoFolderInput(
              page,
              '/tmp/myfolder',
              page.getByTestId('destination-folder-selector'),
            );

            // Then
            await expect(
              page
                .getByTestId('auto-deletion-selector')
                .getByTestId('option-0'),
            ).toHaveClass(/weak-hub-btn/);
            await expect(
              page
                .getByTestId('auto-deletion-selector')
                .getByTestId('option-1'),
            ).toHaveClass(/normal-hub-btn/);

            await expect(
              page.getByText('Default to "Off" on setting change'),
            ).toBeVisible();

            await expect(page.getByTestId('apply-configuration')).toBeEnabled();
            await page.getByTestId('apply-configuration').click();

            await expect(
              page.getByText('Default to "Off" on setting change'),
            ).not.toBeVisible();
          },
        );
        test('Should present deletion message to user while deleting', async ({
          page,
        }) => {
          // Given
          await setupRoutes(page, configuration, deviceList);
          await navigateToInferenceHubAndSelectDevice(page);
          let inferenceSignals = await setInferenceRouteInterceptors(page);
          await loadFileIntoFileInput(
            page,
            'samples/configuration_det.json',
            page.getByTestId('ppl-file-select-btn'),
          );
          await page.getByTestId('ai-model-type-selector').click();
          await page
            .locator('mat-option', { hasText: 'Brain Builder Detector' })
            .click();

          // Then
          await expect(page.getByTestId('deletion-notice')).not.toBeVisible();

          // When
          await page
            .getByTestId('auto-deletion-selector')
            .getByTestId('option-0')
            .click();
          await page.getByRole('button', { name: 'Enable' }).click();
          await page.getByRole('button', { name: 'Apply' }).click();
          await page.getByRole('button', { name: 'Start' }).click();

          // Then
          await expect(page.getByTestId('deletion-notice')).toBeVisible();
        });

        // @ACC_ADI-1677
        test(
          'Given User has not selected a device and operation mode is "Image capture", ' +
            '"Start" button is  disabled.',
          async ({ page }) => {
            await setupRoutes(page, configuration, deviceList);
            await page.goto('http://localhost:4200/');
            await page.getByRole('link', { name: 'Inference' }).click();

            await page.getByTestId('ai-model-type-selector').click();
            await page
              .locator('mat-option', { hasText: 'Image Capture' })
              .click();

            await expect(
              page.getByTestId('start-inference-btn'),
            ).toBeDisabled();
          },
        );

        test('Should show JSON when F is 1 and inference is an object', async ({
          page,
        }) => {
          const mockInference = [
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
          ];

          await setupRoutes(page, configuration, deviceList);
          await navigateToInferenceHubAndSelectDevice(page);
          await setInferenceRouteInterceptors(page, true, mockInference);
          await page.getByTestId('ai-model-type-selector').click();
          await page
            .locator('mat-option', { hasText: 'Brain Builder Detector' })
            .click();

          await loadFileIntoFileInput(
            page,
            'samples/configuration_class.json',
            page.getByTestId('ppl-file-select-btn'),
          );

          // apply PPL parameter
          await expect(page.getByTestId('apply-configuration')).toBeEnabled();
          await page.getByTestId('apply-configuration').click();

          await expect(page.getByTestId('start-inference-btn')).toBeEnabled();
          await page.getByTestId('start-inference-btn').click();

          //check everything is disabled
          await expect(
            page.getByTestId('ai-model-type-selector'),
          ).toBeDisabled();
          await expect(
            page.getByTestId('label-file-select-btn'),
          ).toBeDisabled();
          await expect(page.getByTestId('ppl-file-select-btn')).toBeDisabled();
          await expect(
            page.getByTestId('destination-folder-selector'),
          ).toBeDisabled();
          await expect(page.getByTestId('quota-spinner')).toBeDisabled();
          await expect(
            page.getByTestId('auto-deletion-selector'),
          ).toBeDisabled();

          //check inference is shown in json

          await page
            .locator('app-inference-display')
            .locator('button', { hasText: 'Json' }) // matching is case-insensitive
            .click();
          const JSONcontents = page.locator('app-inference-display');

          // Get the rendered inference data
          const receivedInfJson: Detection = JSON.parse(
            (
              await JSONcontents.locator('span > .content').allInnerTexts()
            ).join(''),
          );
          expect(
            receivedInfJson.perception.object_detection_list,
          ).toMatchObject(mockInference);
        });

        test('Should show JSON when F is 1 and inference is an object and detection is generic', async ({
          page,
        }) => {
          const mockInference = [
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
          ];

          configuration.vapp_type = 'generic_detection';
          await setupRoutes(page, configuration, deviceList);
          await navigateToInferenceHubAndSelectDevice(page);
          await setInferenceRouteInterceptors(page, true, mockInference);
          await page.getByTestId('ai-model-type-selector').click();
          await page
            .locator('mat-option', { hasText: 'Object Detection' })
            .click();

          await loadFileIntoFileInput(
            page,
            'samples/configuration_class.json',
            page.getByTestId('ppl-file-select-btn'),
          );

          // apply PPL parameter
          await expect(page.getByTestId('apply-configuration')).toBeEnabled();
          await page.getByTestId('apply-configuration').click();

          await expect(page.getByTestId('start-inference-btn')).toBeEnabled();
          await page.getByTestId('start-inference-btn').click();

          //check everything is disabled
          await expect(
            page.getByTestId('ai-model-type-selector'),
          ).toBeDisabled();
          await expect(
            page.getByTestId('label-file-select-btn'),
          ).toBeDisabled();
          await expect(page.getByTestId('ppl-file-select-btn')).toBeDisabled();
          await expect(
            page.getByTestId('destination-folder-selector'),
          ).toBeDisabled();
          await expect(page.getByTestId('quota-spinner')).toBeDisabled();
          await expect(
            page.getByTestId('auto-deletion-selector'),
          ).toBeDisabled();

          //check inference is shown in json

          await page
            .locator('app-inference-display')
            .locator('button', { hasText: 'Json' }) // matching is case-insensitive
            .click();
          const JSONcontents = page.locator('app-inference-display');

          // Get the rendered inference data
          const receivedInfJson: Detection = JSON.parse(
            (
              await JSONcontents.locator('span > .content').allInnerTexts()
            ).join(''),
          );
          expect(
            receivedInfJson.perception.object_detection_list,
          ).toMatchObject(mockInference);
        });

        test('Should show JSON when F is 1 and inference is a string', async ({
          page,
        }) => {
          const mockInference = `[
            {
              "class_id": 3,
              "bounding_box_type": "BoundingBox2d",
              "bounding_box": { "left": 0, "top": 0, "right": 100, "bottom": 100 },
              "score": 0
            },
            {
              "class_id": 1,
              "bounding_box_type": "BoundingBox2d",
              "bounding_box": { "left": 0, "top": 0, "right": 100, "bottom": 100 },
              "score": 0
            }
          ]`;

          await setupRoutes(page, configuration, deviceList);
          await navigateToInferenceHubAndSelectDevice(page);
          await setInferenceRouteInterceptors(page, true, mockInference);
          await page.getByTestId('ai-model-type-selector').click();
          await page
            .locator('mat-option', { hasText: 'Brain Builder Detector' })
            .click();

          await loadFileIntoFileInput(
            page,
            'samples/configuration_class.json',
            page.getByTestId('ppl-file-select-btn'),
          );

          // apply PPL parameter
          await expect(page.getByTestId('apply-configuration')).toBeEnabled();
          await page.getByTestId('apply-configuration').click();

          await expect(page.getByTestId('start-inference-btn')).toBeEnabled();
          await page.getByTestId('start-inference-btn').click();

          //check everything is disabled
          await expect(
            page.getByTestId('ai-model-type-selector'),
          ).toBeDisabled();
          await expect(
            page.getByTestId('label-file-select-btn'),
          ).toBeDisabled();
          await expect(page.getByTestId('ppl-file-select-btn')).toBeDisabled();
          await expect(
            page.getByTestId('destination-folder-selector'),
          ).toBeDisabled();
          await expect(page.getByTestId('quota-spinner')).toBeDisabled();
          await expect(
            page.getByTestId('auto-deletion-selector'),
          ).toBeDisabled();

          //check inference is shown in json

          await page
            .locator('app-inference-display')
            .locator('button', { hasText: 'Json' }) // matching is case-insensitive
            .click();
          const JSONcontents = page.locator('app-inference-display');

          // Get the rendered inference data
          const receivedInfJson: Detection = JSON.parse(
            (
              await JSONcontents.locator('span > .content').allInnerTexts()
            ).join(''),
          );
          expect(
            receivedInfJson.perception.object_detection_list,
          ).toMatchObject(JSON.parse(mockInference));
        });
      },
    );

    test.describe(
      'Sad paths',
      {
        annotation: {
          type: 'Sad paths',
          description: 'These tests showcase edge case operation',
        },
      },
      () => {
        let configuration: Configuration;

        const deviceList = DeviceList.sample();

        test.beforeEach(() => {
          configuration = {
            device_dir_path: '/tmp/local-console',
            size: 100,
            unit: 'MB',
            vapp_type: 'classification',
            vapp_config_file: null,
            vapp_labels_file: null,
          };
        });

        // @ACC_ADI-1616
        test(
          'Given User has deployed classification AI model, Edge App and PPL Parameters, ' +
            'When User tries to start inference, ' +
            'Then Inference stops.',
          async ({ page }) => {
            await setupRoutes(page, configuration, deviceList);
            await navigateToInferenceHubAndSelectDevice(page);

            await loadFileIntoFileInput(
              page,
              'samples/configuration_det.json',
              page.getByTestId('ppl-file-select-btn'),
            );

            await expect(page.getByTestId('apply-configuration')).toBeEnabled();
            await page.getByTestId('apply-configuration').click();

            let { isInferenceListCalled, isInferenceToJsonCalled } =
              await setInferenceRouteInterceptors(page, false);

            await expect(page.getByTestId('drawing')).not.toHaveClass(
              /(^|\s)error(\s|$)/,
            );

            await expect(page.getByTestId('start-inference-btn')).toBeEnabled();
            await page.getByTestId('start-inference-btn').click();

            await expect(page.getByTestId('drawing')).toHaveClass(
              /(^|\s)error(\s|$)/,
            );
            await expect(page.locator('app-inference-display')).toContainText(
              'Failed to Process Data.',
            );
            await expect(isInferenceListCalled).resolves.toBeTruthy();
            await expect(isInferenceToJsonCalled).resolves.toBeTruthy();
          },
        );

        test('Should show error when P does not match operation mode', async ({
          page,
        }) => {
          const mockInference = [
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
          ];

          await setupRoutes(page, configuration, deviceList);
          await navigateToInferenceHubAndSelectDevice(page);
          await setInferenceRouteInterceptors(
            page,
            true,
            mockInference,
            1,
            TaskType.Classification,
          );
          await page.getByTestId('ai-model-type-selector').click();
          await page
            .locator('mat-option', { hasText: 'Brain Builder Detector' })
            .click();

          await loadFileIntoFileInput(
            page,
            'samples/configuration_class.json',
            page.getByTestId('ppl-file-select-btn'),
          );

          // apply PPL parameter
          await expect(page.getByTestId('apply-configuration')).toBeEnabled();
          await page.getByTestId('apply-configuration').click();

          await expect(page.getByTestId('start-inference-btn')).toBeEnabled();
          await page.getByTestId('start-inference-btn').click();

          //check everything is disabled
          await expect(
            page.getByTestId('ai-model-type-selector'),
          ).toBeDisabled();
          await expect(
            page.getByTestId('label-file-select-btn'),
          ).toBeDisabled();
          await expect(page.getByTestId('ppl-file-select-btn')).toBeDisabled();
          await expect(
            page.getByTestId('destination-folder-selector'),
          ).toBeDisabled();
          await expect(page.getByTestId('quota-spinner')).toBeDisabled();
          await expect(
            page.getByTestId('auto-deletion-selector'),
          ).toBeDisabled();

          //check error is shown in inference display
          const JSONcontents = page.locator('app-inference-display div');

          // Get the inference error
          const errorInference: string[] = await JSONcontents.allInnerTexts();
          expect(errorInference).toContainEqual(
            'The task type reported by the application running in the device is classification, but detection was expected for the given Operation Mode.',
          );
        });

        test('Should show error when P is custom and F is 0', async ({
          page,
        }) => {
          const mockInference = [
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
          ];

          await setupRoutes(page, configuration, deviceList);
          await navigateToInferenceHubAndSelectDevice(page);
          await setInferenceRouteInterceptors(
            page,
            false,
            mockInference,
            0,
            TaskType.Custom,
          );
          await page.getByTestId('ai-model-type-selector').click();
          await page.locator('mat-option', { hasText: 'User App' }).click();

          await loadFileIntoFileInput(
            page,
            'samples/configuration_class.json',
            page.getByTestId('ppl-file-select-btn'),
          );

          // apply PPL parameter
          await expect(page.getByTestId('apply-configuration')).toBeEnabled();
          await page.getByTestId('apply-configuration').click();

          await expect(page.getByTestId('start-inference-btn')).toBeEnabled();
          await page.getByTestId('start-inference-btn').click();

          //check everything is disabled
          await expect(
            page.getByTestId('ai-model-type-selector'),
          ).toBeDisabled();
          await expect(page.getByTestId('ppl-file-select-btn')).toBeDisabled();
          await expect(
            page.getByTestId('destination-folder-selector'),
          ).toBeDisabled();
          await expect(page.getByTestId('quota-spinner')).toBeDisabled();
          await expect(
            page.getByTestId('auto-deletion-selector'),
          ).toBeDisabled();

          const JSONcontents = page.locator('app-inference-display');

          // Get the rendered inference data
          const receivedErrorJson: Detection = JSON.parse(
            (
              await JSONcontents.locator('span > .content').allInnerTexts()
            ).join(''),
          );

          expect(receivedErrorJson).toEqual(
            JSON.parse(
              `{"errorLabel": "Only JSON allowed for Custom Operation Mode (Flatbuffer detected in the inferences)"}`,
            ),
          );
        });

        test('Should show JSON error when F is 1 and inference is a not parseable string to json', async ({
          page,
        }) => {
          const mockInference = `this is not a json`;

          await setupRoutes(page, configuration, deviceList);
          await navigateToInferenceHubAndSelectDevice(page);
          await setInferenceRouteInterceptors(page, true, mockInference);
          await page.getByTestId('ai-model-type-selector').click();
          await page
            .locator('mat-option', { hasText: 'Brain Builder Detector' })
            .click();

          await loadFileIntoFileInput(
            page,
            'samples/configuration_class.json',
            page.getByTestId('ppl-file-select-btn'),
          );

          // apply PPL parameter
          await expect(page.getByTestId('apply-configuration')).toBeEnabled();
          await page.getByTestId('apply-configuration').click();

          await expect(page.getByTestId('start-inference-btn')).toBeEnabled();
          await page.getByTestId('start-inference-btn').click();

          //check everything is disabled
          await expect(
            page.getByTestId('ai-model-type-selector'),
          ).toBeDisabled();
          await expect(
            page.getByTestId('label-file-select-btn'),
          ).toBeDisabled();
          await expect(page.getByTestId('ppl-file-select-btn')).toBeDisabled();
          await expect(
            page.getByTestId('destination-folder-selector'),
          ).toBeDisabled();
          await expect(page.getByTestId('quota-spinner')).toBeDisabled();
          await expect(
            page.getByTestId('auto-deletion-selector'),
          ).toBeDisabled();

          //check error is shown in inference display

          const JSONcontents = page.locator('app-inference-display div');

          // Get the inference error
          const errorInference: string[] = await JSONcontents.allInnerTexts();
          expect(errorInference).toContainEqual(
            'Unable to parse metadata contents. Only UTF-8 encoded JSON is supported. Please contact Edge App supplier for more information.',
          );
        });

        test('Should show JSON error when F is 1 and inference is a not a JSON object', async ({
          page,
        }) => {
          const mockInference = '[{ hello: 0 ]';

          await setupRoutes(page, configuration, deviceList);
          await navigateToInferenceHubAndSelectDevice(page);
          await setInferenceRouteInterceptors(page, true, mockInference);
          await page.getByTestId('ai-model-type-selector').click();
          await page
            .locator('mat-option', { hasText: 'Brain Builder Detector' })
            .click();

          await loadFileIntoFileInput(
            page,
            'samples/configuration_class.json',
            page.getByTestId('ppl-file-select-btn'),
          );

          // apply PPL parameter
          await expect(page.getByTestId('apply-configuration')).toBeEnabled();
          await page.getByTestId('apply-configuration').click();

          await expect(page.getByTestId('start-inference-btn')).toBeEnabled();
          await page.getByTestId('start-inference-btn').click();

          //check everything is disabled
          await expect(
            page.getByTestId('ai-model-type-selector'),
          ).toBeDisabled();
          await expect(
            page.getByTestId('label-file-select-btn'),
          ).toBeDisabled();
          await expect(page.getByTestId('ppl-file-select-btn')).toBeDisabled();
          await expect(
            page.getByTestId('destination-folder-selector'),
          ).toBeDisabled();
          await expect(page.getByTestId('quota-spinner')).toBeDisabled();
          await expect(
            page.getByTestId('auto-deletion-selector'),
          ).toBeDisabled();

          //check error is shown in inference display

          const JSONcontents = page.locator('app-inference-display div');

          // Get the inference error
          const errorInference: string[] = await JSONcontents.allInnerTexts();
          expect(errorInference).toContainEqual(
            'Unable to parse metadata contents. Only UTF-8 encoded JSON is supported. Please contact Edge App supplier for more information.',
          );
        });

        test.describe('WebSocket tests', () => {
          test('Should show Operation Stopped notification on quota reached', async ({
            page,
            websocketFixture,
          }) => {
            // Given
            const device = deviceList.devices[0];
            let stopCalledTimes = 0;
            await setupRoutes(page, configuration, deviceList);
            await page.route(
              `**/devices/1884/modules/node/property`,
              async (route: Route, request) => {
                const body = route.request().postDataJSON();
                console.log(body);
                if (
                  body?.configuration?.edge_app?.common_settings?.port_settings
                    .metadata.enabled === false
                ) {
                  stopCalledTimes++;
                }
                route.fulfill({ json: { result: 'SUCCESS' }, status: 200 });
              },
            );
            await page.route(
              '**/devices/' + device.device_id,
              async (route: Route) => {
                await route.fulfill({ json: device });
              },
            );
            await page.route(
              `**/devices/${device.device_id}/command`,
              async (route) => {
                route.fulfill();
              },
            );
            await page.goto('http://localhost:4200/');
            await page.getByRole('link', { name: 'Devices' }).click();

            // When we simulate a quota restriction hit
            await fetch(`http://localhost:${websocketFixture}/notify`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                kind: 'storage-limit-hit',
                data: {
                  quota: 10000000,
                  device_id: device.device_id,
                  path: '/etc/some/path',
                },
              }),
            });

            // Then
            await expect(page.getByTestId('user-popup')).toBeVisible();
            await expect(
              page.getByRole('button', { name: 'Storage Settings' }),
            ).toBeVisible();
            await waitForExpect(() => {
              expect(stopCalledTimes).toBe(1);
            });

            // And when
            await page
              .getByRole('button', { name: 'Storage Settings' })
              .click();

            // Then
            await page.waitForURL(`**\/data-hub`);
            await expect(page.getByTestId('storage-settings')).toHaveClass(
              /highlight/,
            );
            await expect(
              page.getByTestId('selected-device').getByTestId('text'),
            ).toContainText(device.device_name);
            await waitForExpect(() => {
              expect(stopCalledTimes).toBe(1);
            });
          });

          test('Should switch to device and stop stream if quota is reached within Inferences', async ({
            page,
            websocketFixture,
          }) => {
            // Given
            const device = deviceList.devices[0];
            let stopCalledTimes = 0;
            await setupRoutes(page, configuration, deviceList);
            await page.route(
              `**/devices/1884/modules/node/property`,
              async (route: Route, request) => {
                const body = route.request().postDataJSON();
                if (
                  body?.configuration?.edge_app?.common_settings?.port_settings
                    .metadata.enabled === false
                ) {
                  stopCalledTimes++;
                }
                route.fulfill({ json: { result: 'SUCCESS' }, status: 200 });
              },
            );
            await page.route(
              '**/devices/' + device.device_id,
              async (route: Route) => {
                await route.fulfill({ json: device });
              },
            );
            await page.route(
              `**/devices/${device.device_id}/command`,
              async (route) => {
                route.fulfill();
              },
            );
            await page.goto('http://localhost:4200/');
            await page.getByRole('link', { name: 'Inference' }).click();

            // When we simulate a quota restriction hit
            await fetch(`http://localhost:${websocketFixture}/notify`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                kind: 'storage-limit-hit',
                data: {
                  quota: 10000000,
                  device_id: device.device_id,
                  path: '/etc/some/path',
                },
              }),
            });

            // Then
            await expect(page.getByTestId('storage-settings')).toHaveClass(
              /highlight/,
            );
            await expect(
              page.getByTestId('selected-device').getByTestId('text'),
            ).toContainText(device.device_name);
            await waitForExpect(() => {
              expect(stopCalledTimes).toBe(1);
            });
          });
        });
      },
    );
  },
);
