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
import { DeviceList } from '@samplers/device';
import { test } from './../fixtures/fixtures';

test.describe(
  'Devices Management Hub',
  {
    annotation: {
      type: 'Devices Management Hub',
      description:
        'This test suit covers the FrontEnd tests involving the Devices Management Hub tab',
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
          'Select a device',
          {
            annotation: {
              type: 'Select a device',
              description:
                'This test checks that, when a device is selected, the device information pane comes into view.',
            },
          },
          async ({ page }) => {
            const deviceList = DeviceList.sample();
            deviceList.devices = [deviceList.devices[0]];
            await page.route('**/devices?limit=500', async (route) => {
              await route.fulfill({ json: deviceList });
            });

            await page.goto('http://localhost:4200/device-management');
            await page.getByRole('link', { name: 'Devices' }).click();
            await page.getByText('Connected').click();
            await expect(
              page.getByRole('cell', { name: 'Hardware' }),
              "The 'Hardware' section of the devices info should be in the viewport.",
            ).toBeInViewport();
          },
        );
      },
    );
  },
);
