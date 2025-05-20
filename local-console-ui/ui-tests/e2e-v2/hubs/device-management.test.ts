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
import { checkDeviceTabs } from '../../tools/checks';
import {
  createDevice,
  loadFileIntoFileInput,
  selectDefaultDevice,
} from '../../tools/interactions';

test.describe(
  'Devices Management Hub',
  {
    annotation: {
      type: 'Devices Management Hub',
      description:
        'This test suit covers all E2E (FrontEnd + BackEnd) tests involving the Devices Management Hub tab',
    },
  },
  () => {
    test.describe(
      'Happy paths',
      {
        annotation: {
          type: 'Happy paths',
          description:
            'These tests cover situations where the user is using the Devices Management Hub properly, and they achieve the expected result',
        },
      },
      () => {
        test(
          'Delete device from management',
          {
            annotation: {
              type: 'Delete device from management',
              description:
                'This creates a new device, which is then deleted to make sure that the delete process works as expected.',
            },
          },
          async ({ page, fixture }) => {
            // We create an additional device to be removed (as there must always be at least one device)
            const deviceName: string = 'devicename_42';
            const devicePort: number = 1885;
            await page.goto('http://localhost:4200/provisioning-hub');
            await createDevice(page, deviceName, devicePort);

            // We make sure the device exists
            await page.goto('http://localhost:4200/device-management');
            await expect(
              page
                .getByRole('row', { name: deviceName + ' Disconnected' })
                .getByRole('button'),
              'A new device with the given name should exist.',
            ).toBeVisible();

            // The device is deleted
            await page
              .getByRole('row', { name: deviceName + ' Disconnected' })
              .getByRole('button')
              .click();
            await page.getByRole('menuitem', { name: 'Delete' }).click();
            await page.getByRole('button', { name: 'Delete' }).click();

            // We make sure the device no longer is listed
            await expect(
              page
                .getByRole('row', { name: deviceName + ' Disconnected' })
                .getByRole('button'),
              'The device created in this test should be properly deleted.',
            ).not.toBeVisible();
          },
        );

        test(
          'Rename device',
          {
            annotation: {
              type: 'Rename device',
              description:
                'This creates a new device, which is then renamed to make sure that the renaming process works as expected. Finally, the device is removed to prevent affecting other tests.',
            },
          },
          async ({ page, fixture }) => {
            // We create an additional device to be removed (as there must always be at least one device)
            const firstName: string = 'devicename_42';
            const secondName: string = 'devicename_43';
            const devicePort: number = 1885;
            await page.goto('http://localhost:4200/provisioning-hub');
            await createDevice(page, firstName, devicePort);

            // We make sure a device with the old name exists, and a device with the new name doesn't
            await page.goto('http://localhost:4200/device-management');
            await expect(
              page
                .getByRole('row', { name: firstName + ' Disconnected' })
                .getByRole('button'),
              'A device with the name used to create a device should exist.',
            ).toBeVisible();
            await expect(
              page
                .getByRole('row', { name: secondName + ' Disconnected' })
                .getByRole('button'),
              'A device with the new name that will be using in the renaming should not exist.',
            ).not.toBeVisible();

            // The device is renamed
            await page
              .getByRole('row', { name: firstName + ' Disconnected' })
              .getByRole('button')
              .click();
            await page.getByRole('menuitem', { name: 'Rename' }).click();
            await page.getByRole('textbox', { name: firstName }).click();
            await page
              .getByRole('textbox', { name: firstName })
              .fill(secondName);
            await page.getByRole('button', { name: 'Rename' }).click();

            // We make sure a device with the new name exists, and the device with the old name doesn't
            await expect(
              page
                .getByRole('row', { name: secondName + ' Disconnected' })
                .getByRole('button'),
              'A device with the new name used in the renaming should exist.',
            ).toBeVisible();
            await expect(
              page
                .getByRole('row', { name: firstName + ' Disconnected' })
                .getByRole('button'),
              'A device with the first name from before the renaming should not exist.',
            ).not.toBeVisible();

            const response = await page.request.delete(
              `http://localhost:8000/devices/${devicePort}`,
            );
            expect(
              response.status(),
              'A 200 status should be received when deleting the device at the end of the test.',
            ).toBe(200);
          },
        );

        test(
          'Check MQTT broker info',
          {
            annotation: {
              type: 'Check MQTT broker info',
              description:
                'This creates a new device, selects it in the Device Hub, and checks the Broker ID and Broker Port are the correct ones on the network tab. Finally, the device is removed to prevent affecting other tests.',
            },
          },
          async ({ page, fixture }) => {
            // Create a new, empty device, to the broker-id is not yet modified
            const deviceName: string = 'devicename_42';
            const devicePort: number = 1885;
            await page.goto('http://localhost:4200/provisioning-hub');
            await createDevice(page, deviceName, devicePort);

            // Continue with the test itself
            await page.goto('http://localhost:4200/device-management');

            await page
              .getByRole('cell', { name: deviceName })
              .locator('app-icon-text')
              .click();

            await page.getByTestId('network_tab').click();

            await expect(
              page.getByTestId('broker-id'),
              "The Broker ID should match the expected value of 'localhost'",
            ).toContainText('localhost');
            await expect(
              page.getByTestId('broker-port'),
              'The Broker Port should be empty',
            ).toContainText('' + devicePort);

            const response = await page.request.delete(
              `http://localhost:8000/devices/${devicePort}`,
            );
            expect(
              response.status(),
              'A 200 status should be received when deleting the device at the end of the test.',
            ).toBe(200);
          },
        );

        //@ACC_PFREQ-1512.2
        test(
          'Complete device information',
          {
            annotation: {
              type: 'Complete device information',
              description:
                'This test checks that the information of the Default device is correct on the device, network and AI model tabs.',
            },
          },
          async ({ page, fixture }) => {
            test.skip(
              fixture.ECIfVersion != 1,
              'FIXME: only for v1 for the moment (v2 model OTA impl missing)',
            );

            await fixture.waitForDeviceReady(
              Object.keys(fixture.devices).map(Number)[0],
            );
            await page.goto('http://localhost:4200');

            //Deploy a model to be able to check AI tab device information
            await page.getByRole('link', { name: 'Deployment' }).click();

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
            //deploy it
            await page.getByRole('button', { name: 'Deploy' }).click();

            await expect(page.locator('tbody')).not.toBeEmpty();

            await expect(page.locator('tbody')).not.toContainText(
              DeploymentStatusOut.Running,
              { timeout: 0 },
            );

            // Confirm deploy
            await expect(
              page.locator('app-deployment-list').locator('tbody'),
            ).toContainText(DeploymentStatusOut.Success);

            //change to Devices hub
            await page.getByRole('link', { name: 'Devices' }).click();

            //select a device
            await page
              .getByRole('cell', { name: 'Default' })
              .locator('app-icon-text')
              .click();

            checkDeviceTabs(page, dut, fixture.server.host);
          },
        );
      },
    );
  },
);
