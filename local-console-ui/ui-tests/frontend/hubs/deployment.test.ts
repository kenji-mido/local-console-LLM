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

import {
  DeviceListV2,
  DeviceStatus,
  DeviceType,
  LocalDevice,
} from '@app/core/device/device';
import { expect, Locator, Page, Route } from '@playwright/test';
import { DeployHistoriesOutList } from '@samplers/deployment';
import { Device } from '@samplers/device';
import { test } from './../fixtures/fixtures';

test.describe(
  'Deployment screen',
  {
    annotation: {
      type: 'Deployment screen',
      description:
        'This test suit covers the FrontEnd tests involving the deployment of models, apps and firmware to devices',
    },
  },
  () => {
    let device: LocalDevice;
    let fileInputLocator: (locator: string) => Locator;

    test.beforeEach(async ({ page }) => {
      device = Device.sample({
        connection_state: DeviceStatus.Disconnected,
      });
      await page.route('**/health', async (route: Route) => {
        await route.fulfill();
      });
      await page.route('**/deploy_history?limit=256', async (route: Route) => {
        await route.fulfill({
          json: DeployHistoriesOutList.sampleHistories([device]),
        });
      });
      await page.route('**/devices?limit=500', async (route) => {
        await route.fulfill({ json: <DeviceListV2>{ devices: [device] } });
      });
      await page.route(
        `**/devices/${device.device_id}/configuration`,
        async (route) => {
          await route.fulfill({ json: { result: 'SUCCESS' } });
        },
      );
      fileInputLocator = (locator: string) => {
        return getFileInputActuator(page, locator);
      };
    });

    test.describe('Happy paths', () => {
      test('Should disable Model and App deployment if RasPI', async ({
        page,
      }) => {
        device.device_type = DeviceType.T3P_LUCID; // Any OTHER than Raspi
        device.connection_state = DeviceStatus.Connected;
        await navigateAndSetDefaults(page);

        await expect(
          getFileInputActuator(page, 'model-selector'),
        ).toBeEnabled();
        await expect(getFileInputActuator(page, 'app-selector')).toBeEnabled();
        await expect(
          getFileInputActuator(page, 'chip-fw-selector'),
        ).toBeEnabled();
        await expect(
          getFileInputActuator(page, 'sensor-fw-selector'),
        ).toBeEnabled();
      });
    });

    test.describe('Sad paths', () => {
      test('Should disable Deploy button if device is Connecting', async ({
        page,
      }) => {
        device.connection_state = DeviceStatus.Connecting;
        await navigateAndSetDefaults(page);

        await expect(fileInputLocator('model-selector')).toBeDisabled();
        await expect(fileInputLocator('app-selector')).toBeDisabled();
        await expect(fileInputLocator('chip-fw-selector')).toBeDisabled();
        await expect(fileInputLocator('sensor-fw-selector')).toBeDisabled();
        await expect(
          page.getByRole('button', { name: 'Deploy' }),
        ).toBeDisabled();
      });

      test('Should disable Deploy button if device is Disconnected', async ({
        page,
      }) => {
        device.connection_state = DeviceStatus.Disconnected;
        await navigateAndSetDefaults(page);

        await expect(fileInputLocator('model-selector')).toBeDisabled();
        await expect(fileInputLocator('app-selector')).toBeDisabled();
        await expect(fileInputLocator('chip-fw-selector')).toBeDisabled();
        await expect(fileInputLocator('sensor-fw-selector')).toBeDisabled();
        await expect(
          page.getByRole('button', { name: 'Deploy' }),
        ).toBeDisabled();
      });

      test('Should disable all deployments if device type is UNKNOWN', async ({
        page,
      }) => {
        device.connection_state = DeviceStatus.Disconnected;
        device.device_type = 'some other unknown type';
        await navigateAndSetDefaults(page);

        await expect(fileInputLocator('model-selector')).toBeDisabled();
        await expect(fileInputLocator('app-selector')).toBeDisabled();
        await expect(fileInputLocator('chip-fw-selector')).toBeDisabled();
        await expect(fileInputLocator('sensor-fw-selector')).toBeDisabled();
        await expect(
          page.getByRole('button', { name: 'Deploy' }),
        ).toBeDisabled();
      });

      test('Should disable OTA Firmware deployment if RasPI', async ({
        page,
      }) => {
        device.device_type = DeviceType.RASPI;
        device.connection_state = DeviceStatus.Connected;
        await navigateAndSetDefaults(page);

        await expect(fileInputLocator('model-selector')).toBeEnabled();
        await expect(fileInputLocator('app-selector')).toBeEnabled();
        await expect(fileInputLocator('chip-fw-selector')).toBeDisabled();
        await expect(fileInputLocator('sensor-fw-selector')).toBeDisabled();
      });
    });
  },
);

function getFileInputActuator(page: Page, locator: string) {
  return page.getByTestId(locator).getByRole('button');
}

async function navigateAndSetDefaults(page: Page) {
  await page.goto('http://localhost:4200/');
  await page.getByRole('link', { name: 'Deployment' }).click();

  // Select a device
  await page.getByTestId('device-selector-btn').click();
  await page.getByTestId('device-selector-option-0').click();
  await page.getByRole('button', { name: 'Select' }).click();

  // Open up FW file inputs
  await page.locator('app-toggle').getByRole('img').click();
}
