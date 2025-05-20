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

import { DeploymentStatusOut } from '@app/core/deployment/deployment';
import { expect } from '@playwright/test';
import { test } from '../../e2e-fixtures/fixtures';
import {
  loadFileIntoFileInput,
  selectDefaultDevice,
} from '../../tools/interactions';

test.describe(
  'Deployment Hub',
  {
    annotation: {
      type: 'Deployment Hub',
      description:
        'This test suite covers all E2E (FrontEnd + BackEnd) tests involving the Deployment Hub tab',
    },
  },

  () => {
    test.beforeEach(async ({ fixture }) => {
      await fixture.waitForDeviceReady(
        Object.keys(fixture.devices).map(Number)[0],
      );
    });
    test.describe(
      'Happy paths',
      {
        annotation: {
          type: 'Happy paths',
          description:
            'These tests cover situations where the user is using the app properly, and they achieve the expected result',
        },
      },
      () => {
        test(
          'Successful model and app deployment test',
          {
            annotation: {
              type: 'Successful model and app deployment test',
              description:
                'This test deploys an AI Model and an Edge App and expects them to be be properly deployed.',
            },
            tag: '@real',
          },
          async ({ page, fixture }) => {
            await page.goto('http://localhost:4200/deployment-hub');

            //select a device
            const deviceName: string = 'Default';
            const devicePort: number = 1883;
            await selectDefaultDevice(page);
            await expect(
              page.getByTestId('select-device-section'),
            ).toContainText(deviceName);

            let dut = fixture.devices[devicePort];

            //select AI model
            await loadFileIntoFileInput(
              page,
              `samples/${dut.sampleFiles['detectionModel']}`,
              page.getByTestId('model-selector'),
            );

            //select Application
            await loadFileIntoFileInput(
              page,
              `samples/${dut.sampleFiles['detectionApp']}`,
              page.getByTestId('app-selector'),
            );

            //deploy
            await page.getByRole('button', { name: 'Deploy' }).click();

            await expect(
              page.locator('td:nth-child(2) > span').first(),
              `The device of the latest deployment must be previously specified one ('${deviceName}')`,
            ).toContainText(deviceName);

            // Check deployed files
            await expect(
              page.locator('tbody'),
              "The file 'app.bin' should appear in the list of deployed files",
            ).toContainText(`${dut.sampleFiles['detectionApp']}`);
            await expect(
              page.locator('tbody'),
              "At least a file of type 'Edge App' must appear in the list of deployed files",
            ).toContainText('Edge App');

            //FIXME Model OTA is not implemented yet for v2
            if (dut.ECIfVersion == 1) {
              await expect(
                page.locator('tbody'),
                "The file 'model.pkg' should appear in the list of deployed files",
              ).toContainText(`${dut.sampleFiles['detectionModel']}`);
              await expect(
                page.locator('tbody'),
                "At least a file of type 'Model' must appear in the list of deployed files",
              ).toContainText('Model');
            }

            await expect(
              page.locator('tbody'),
              'Make sure all the deployments have finished deploying',
            ).not.toContainText(DeploymentStatusOut.Running, { timeout: 0 });

            const status = await page.locator('tbody').innerText();
            expect(
              status,
              'Make sure there are no failing deployments',
            ).not.toContain(DeploymentStatusOut.Error); // matching is case and space sensitive

            expect(status, 'Make sure deployments are successful').toContain(
              DeploymentStatusOut.Success,
            ); // matching is case and space sensitive
          },
        );

        test(
          'Successful sensor firmware deployment test',
          {
            annotation: {
              type: 'Successful sensor firmware deployment test',
              description:
                'This test deploys a Sensor Firmware and expects it to be properly deployed.',
            },
          },
          async ({ page, fixture }) => {
            test.skip(
              fixture.ECIfVersion != 1,
              'FIXME: only for v1 for the moment',
            );

            await page.goto('http://localhost:4200/deployment-hub');

            //select a device
            const deviceName: string = 'Default';
            const devicePort: number = 1883;

            await selectDefaultDevice(page);
            await expect(
              page.getByTestId('select-device-section'),
            ).toContainText(deviceName);

            let dut = fixture.devices[devicePort];

            await page.locator('app-toggle').getByRole('img').click();

            //select sensor fw
            await loadFileIntoFileInput(
              page,
              `samples/${dut.sampleFiles['sensorFw']}`,
              page.getByTestId('sensor-fw-selector'),
            );

            await page.getByRole('textbox', { name: '010707' }).fill('010707');

            //deploy
            await page.getByRole('button', { name: 'Deploy' }).click();
            //confirm deploy
            await page
              .locator('.cdk-dialog-container')
              .getByRole('button', { name: 'Deploy' })
              .click();

            await expect(
              page.locator('td:nth-child(2) > span').first(),
              `The device of the latest deployment must be previously specified one ('${deviceName}')`,
            ).toContainText(deviceName);

            //Check deploy
            await expect(
              page.locator('tbody'),
              'The sensor firmware file should appear in the list of deployed files',
            ).toContainText(`${dut.sampleFiles['sensorFw']}`);

            await expect(
              page.locator('tbody'),
              "At least a file of type 'Firmware' must appear in the list of deployed files",
            ).toContainText('Firmware');

            await expect(
              page.locator('tbody'),
              'Make sure all the deployments have finished deploying',
            ).not.toContainText(DeploymentStatusOut.Running, { timeout: 0 });

            const status = await page.locator('tbody').innerText();
            expect(
              status,
              'Make sure there are no failing deployments',
            ).not.toContain(DeploymentStatusOut.Error); // matching is case and space sensitive

            expect(status, 'Make sure deployments are successful').toContain(
              DeploymentStatusOut.Success,
            ); // matching is case and space sensitive

            await fixture.resetFirmware('sensor', dut);
          },
        );

        test(
          'Successful main firmware deployment test',
          {
            annotation: {
              type: 'Successful main firmware deployment test',
              description:
                'This test deploys a Main Firmware and expects it to be properly deployed.',
            },
            tag: [
              '@T3P', // Artifacts are for T3P MP
              '@slow',
            ],
          },
          async ({ page, fixture }) => {
            test.skip(
              fixture.ECIfVersion != 1,
              'FIXME: only for v1 for the moment',
            );

            await page.goto('http://localhost:4200/deployment-hub');

            //select a device
            const deviceName: string = 'Default';
            const devicePort: number = 1883;

            await selectDefaultDevice(page);
            await expect(
              page.getByTestId('select-device-section'),
            ).toContainText(deviceName);

            let dut = fixture.devices[devicePort];

            await page.locator('app-toggle').getByRole('img').click();

            //select main chip fw
            await loadFileIntoFileInput(
              page,
              `samples/${dut.sampleFiles['mainFw']}`,
              page.getByTestId('chip-fw-selector'),
            );

            await page.getByRole('textbox', { name: 'D700F6' }).fill('0700FE');

            //deploy
            await page.getByRole('button', { name: 'Deploy' }).click();
            //confirm deploy
            await page
              .locator('.cdk-dialog-container')
              .getByRole('button', { name: 'Deploy' })
              .click();

            await expect(
              page.locator('td:nth-child(2) > span').first(),
              `The device of the latest deployment must be previously specified one ('${deviceName}')`,
            ).toContainText(deviceName);

            //Check deploy
            await expect(
              page.locator('tbody'),
              'The main firmware file should appear in the list of deployed files',
            ).toContainText(`${dut.sampleFiles['mainFw']}`);

            await expect(
              page.locator('tbody'),
              "At least a file of type 'Firmware' must appear in the list of deployed files",
            ).toContainText('Firmware');

            await expect(
              page.locator('tbody'),
              'Make sure all the deployments have finished deploying',
            ).not.toContainText(DeploymentStatusOut.Running, { timeout: 0 });

            const status = await page.locator('tbody').innerText();
            expect(
              status,
              'Make sure there are no failing deployments',
            ).not.toContain(DeploymentStatusOut.Error); // matching is case and space sensitive

            expect(status, 'Make sure deployments are successful').toContain(
              DeploymentStatusOut.Success,
            ); // matching is case and space sensitive

            await fixture.resetFirmware('main', dut);
          },
        );
      },
    );

    test.describe(
      'Sad paths',
      {
        annotation: {
          type: 'Sad paths',
          description:
            'These tests cover situations leading to errors due to improper usage of the app, to ensure they are properly handled',
        },
      },
      () => {
        test(
          'Failing model deployment test',
          {
            annotation: {
              type: 'Failing model deployment test',
              description:
                'This test tries to deploy an incorrect AI Model, and expects it to appear as Fail in the deployment list',
            },
          },
          async ({ page, fixture }) => {
            test.skip(
              fixture.ECIfVersion != 1,
              'FIXME: only for v1 for the moment',
            );

            await page.goto('http://localhost:4200/deployment-hub');

            //select a device
            await selectDefaultDevice(page);

            //select AI model
            await loadFileIntoFileInput(
              page,
              'samples/model_fail.pkg',
              page.getByTestId('model-selector'),
            );

            //deploy
            await page.getByRole('button', { name: 'Deploy' }).click();

            //expects
            await expect(
              page.locator('td:nth-child(4)').first(),
              'Make sure the latest deployment is an AI Model one',
            ).toContainText('AI Model', { timeout: 10000 });
            await expect(
              page.locator('td:nth-child(5)').first(),
              "Make sure the latest deployment is deploying the 'model_fail.pkl' file",
            ).toContainText('model_fail.pkg');

            await page.getByRole('button', { name: 'Refresh' }).click();

            await expect(
              page.locator('tbody'),
              'Make sure all the deployments have finished deploying',
            ).not.toContainText(DeploymentStatusOut.Running, { timeout: 0 });

            await expect(
              page.locator('td:nth-child(3)').first(),
              'Make sure the latest deployment has failed',
            ).toContainText(DeploymentStatusOut.Error);
          },
        );

        test(
          'Failing main chip firmware deployment test',
          {
            annotation: {
              type: 'Failing main chip firmware deployment test',
              description:
                'This test tries to deploy an incorrect Main Chip Firmware, and expects it to appear as Fail in the deployment list',
            },
          },
          async ({ page, fixture }) => {
            test.skip(
              fixture.ECIfVersion != 1,
              'FIXME: only for v1 for the moment',
            );

            await page.goto('http://localhost:4200/deployment-hub');

            //select a device
            await selectDefaultDevice(page);
            await expect(
              page.getByTestId('select-device-section'),
            ).toContainText('Default');

            //select main chip fw
            await page.locator('app-toggle').getByRole('img').click();

            await loadFileIntoFileInput(
              page,
              'samples/firmware_fail.bin',
              page.getByTestId('chip-fw-selector'),
            );

            await page.locator('#mat-input-0').fill('1.0.0');

            //deploy + confirm deploy
            await page.getByRole('button', { name: 'Deploy' }).click();
            await page
              .locator('.cdk-dialog-container')
              .getByRole('button', { name: 'Deploy' })
              .click();

            //expects
            await expect(page.locator('td:nth-child(5)').first()).toContainText(
              'firmware_fail.bin',
              { timeout: 10000 },
            );
            await page.getByRole('button', { name: 'Refresh' }).click();

            await expect(
              page.locator('tbody'),
              'Make sure all the deployments have finished deploying',
            ).not.toContainText(DeploymentStatusOut.Running, { timeout: 0 });

            await expect(page.locator('td:nth-child(3)').first()).toContainText(
              DeploymentStatusOut.Error,
            );
          },
        );

        test(
          'Failing edge app deployment test',
          {
            annotation: {
              type: 'Failing edge app deployment test',
              description:
                'This test tries to deploy an incorrect Edge App, and expects it to appear as Fail in the deployment list',
            },
          },
          async ({ page, fixture }) => {
            await page.goto('http://localhost:4200/deployment-hub');

            //select a device
            await selectDefaultDevice(page);
            await expect(
              page.getByTestId('select-device-section'),
            ).toContainText('Default');

            //select Application
            await loadFileIntoFileInput(
              page,
              'samples/app_fail.aot',
              page.getByTestId('app-selector'),
            );

            //deploy
            await page.getByRole('button', { name: 'Deploy' }).click();

            //expects
            await expect(page.locator('td:nth-child(3)').first()).toContainText(
              DeploymentStatusOut.Running,
              { timeout: 10000 },
            );

            await expect(page.locator('td:nth-child(4)').first()).toContainText(
              'Edge App',
            );
            await expect(page.locator('td:nth-child(5)').first()).toContainText(
              'app_fail.aot',
            );

            await page.getByRole('button', { name: 'Refresh' }).click();

            await expect(
              page.locator('tbody'),
              'Make sure all the deployments have finished deploying',
            ).not.toContainText(DeploymentStatusOut.Running, { timeout: 0 });

            await expect(page.locator('td:nth-child(3)').first()).toContainText(
              DeploymentStatusOut.Error,
              { timeout: 60000 },
            );
          },
        );

        test(
          'Failing sensor chip firmware deployment test',
          {
            annotation: {
              type: 'Failing sensor chip firmware deployment test',
              description:
                'This test tries to deploy an incorrect Sensor Chip Firmware, and expects it to appear as Fail in the deployment list',
            },
          },
          async ({ page, fixture }) => {
            test.skip(
              fixture.ECIfVersion != 1,
              'FIXME: only for v1 for the moment',
            );

            await page.goto('http://localhost:4200/deployment-hub');

            //select a device
            await selectDefaultDevice(page);
            await expect(
              page.getByTestId('select-device-section'),
            ).toContainText('Default');

            //select main chip fw
            await page.locator('app-toggle').getByRole('img').click();

            await loadFileIntoFileInput(
              page,
              'samples/firmware_fail.fpk',
              page.getByTestId('sensor-fw-selector'),
            );

            await page.locator('#mat-input-1').fill('1.0.0');

            //deploy + confirm deploy
            await page.getByRole('button', { name: 'Deploy' }).click();
            await page
              .locator('.cdk-dialog-container')
              .getByRole('button', { name: 'Deploy' })
              .click();

            //expects
            await expect(page.locator('td:nth-child(5)').first()).toContainText(
              'firmware_fail.fpk',
            );

            await page.getByRole('button', { name: 'Refresh' }).click();

            await expect(
              page.locator('tbody'),
              'Make sure all the deployments have finished deploying',
            ).not.toContainText(DeploymentStatusOut.Running, { timeout: 0 });

            await expect(page.locator('td:nth-child(3)').first()).toContainText(
              DeploymentStatusOut.Error,
              { timeout: 10000 },
            );
          },
        );
      },
    );
  },
);
