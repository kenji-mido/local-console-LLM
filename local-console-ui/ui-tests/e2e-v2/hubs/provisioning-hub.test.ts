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

import { expect } from '@playwright/test';
import { test } from '../../e2e-fixtures/fixtures';
import { createDevice } from '../../tools/interactions';

test.describe(
  'Provisioning Hub',
  {
    annotation: {
      type: 'Provisioning Hub',
      description:
        'This test suit covers all E2E (FrontEnd + BackEnd) tests involving the Provisioning Hub tab',
    },
  },
  () => {
    test.describe(
      'Happy paths',
      {
        annotation: {
          type: 'Happy paths',
          description:
            'These tests cover situations where the user is using the Provisioning Hub properly, and they achieve the expected result',
        },
      },
      () => {
        test(
          'Devices are created',
          {
            annotation: {
              type: 'Devices are created',
              description:
                'This tests makes sure that when devices are created, they appear properly listed.',
            },
          },
          async ({ page, fixture }) => {
            await page.goto('http://localhost:4200/provisioning-hub');
            await page.getByTestId('option-1').click();

            // Default device
            await expect(
              page.getByText('1883', { exact: true }).isVisible(),
              "A device with the new port '1883' should appear.",
            ).toBeTruthy();

            // Create new device
            await page.getByTestId('option-0').click();
            await createDevice(page, 'MyDevice', 1884);

            // New device is automatically selected
            await expect(
              page.getByText('1884', { exact: true }).isVisible(),
              "A device with the new port '1884' should appear.",
            ).toBeTruthy();
          },
        );

        // @ACC_PFREQ-1510.2
        test(
          'Preview button is enabled if device is connected',
          {
            annotation: {
              type: 'Preview button is enabled if device is connected',
              description:
                'This test checks whether the Preview button is enabled when the device has connected.',
            },
          },
          async ({ page, fixture }) => {
            // When
            await fixture.waitForDeviceReady(
              Object.keys(fixture.devices).map(Number)[0],
            );
            await page.goto('http://localhost:4200/provisioning-hub');
            await page.getByTestId('option-1').click();
            await expect(page.getByLabel('Start preview')).toBeEnabled();
          },
        );

        test.fixme(
          'Start stream preview',
          {
            annotation: {
              type: 'Start stream preview',
              description:
                'This test checks whether a visualization stream can be started on the Default device.',
            },
          },
          async ({ page, fixture }) => {
            // When
            await fixture.waitForDeviceReady(
              Object.keys(fixture.devices).map(Number)[0],
            );
            await page.goto('http://localhost:4200/provisioning-hub');
            await page.getByTestId('option-1').click();
            await page.getByLabel('Start preview').isEnabled();
            await page.getByLabel('Start preview').click();

            // Then
            await expect(page.getByTestId('drawing')).toHaveClass(/streaming/);
            await expect(page.getByTestId('drawing-surface')).toBeVisible({
              timeout: 60000,
            });
            const canvasLocator = page.getByTestId('drawing-surface');

            await expect
              .poll(async () => {
                return await canvasLocator.evaluate((element) => {
                  const canvas = element as HTMLCanvasElement;
                  const context = canvas.getContext('2d');
                  if (!context) return false;
                  const pixelBuffer = new Uint32Array(
                    context.getImageData(
                      0,
                      0,
                      canvas.width,
                      canvas.height,
                    ).data.buffer,
                  );

                  return pixelBuffer.some((pixel) => pixel !== 0); // Returns true if canvas has drawing
                });
              }, 'An image should appear in the streaming canvas.')
              .toBe(true);
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
          'Device registration raises error when using already used port',
          {
            annotation: {
              type: 'Device registration raises error when using already used port',
              description:
                'This test checks that when attempting to create a device on an already used port, an error is raised and the device is not created.',
            },
          },
          async ({ page, fixture }) => {
            const deviceName: string = 'uniquename_42';
            const devicePort: string = '1885';

            await page.goto('http://localhost:4200/provisioning-hub');

            await page.getByTestId('option-0').click();
            createDevice(page, deviceName, 1883);
            await expect(
              page.locator('.cdk-dialog-container'),
              'After attempting to create a device with an already used port, a pop up should be visible.',
            ).toBeVisible();
            await expect(
              page.getByText('Specified port 1883 is'),
              "An error message containing 'Specified port 1883 is' should appear.",
            ).toBeVisible();
            await page.getByRole('button', { name: 'OK' }).click();

            await page
              .getByTestId('device-register-port')
              .getByPlaceholder('1883')
              .click();
            await page
              .getByTestId('device-register-port')
              .getByPlaceholder('1883')
              .fill(devicePort);
            await page.getByTestId('device-register').click();

            await page.getByTestId('option-1').click();
            await page.locator('.mat-mdc-select-arrow-wrapper').click();
            await expect(
              page.getByRole('option', {
                name: deviceName + ' (MQTT port: ' + devicePort + ')',
              }),
              'Once a valid port is used, a new device should be properly created, and appear listed.',
            ).toBeVisible();

            const response = await page.request.delete(
              `http://localhost:8000/devices/${devicePort}`,
            );
            expect(
              response.status(),
              'A 200 status should be received when deleting the device at the end of the test.',
            ).toBe(200);
          },
        );
      },
    );
  },
);
