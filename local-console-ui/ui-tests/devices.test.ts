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

import { test, expect, Page, Locator } from '@playwright/test';
import { DeploymentStatusOut } from '@app/core/deployment/deployment';
import { join } from 'path';

test('Complete device information', async ({ page }) => {
  await page.goto('http://localhost:4200/device-management');

  //select a device
  await page
    .getByRole('cell', { name: 'Default' })
    .locator('app-icon-text')
    .click();

  console.log(page.getByTestId('sensor'));
  console.log(page.getByTestId('main_chip'));
  console.log(page.getByTestId('sensor_fw_main'));
  console.log(page.getByTestId('sensor_fw_loader'));
  console.log(page.getByTestId('processing_state'));
  console.log(page.getByTestId('device_id'));
  console.log(page.getByTestId('internal_id'));

  await expect(page.getByTestId('sensor')).toContainText('IMX500');
  await expect(page.getByTestId('main_chip')).toContainText('D52408');
  await expect(page.getByTestId('sensor_fw_main')).toContainText('020000');
  await expect(page.getByTestId('sensor_fw_loader')).toContainText('020301');
  await expect(page.getByTestId('processing_state')).toContainText('Idle');
  await expect(page.getByTestId('device_id')).toContainText('1883');
  await expect(page.getByTestId('internal_id')).toContainText('1883');

  await page.getByTestId('network_tab').click();

  await expect(page.getByTestId('ntp-server')).toContainText(' ');
  await expect(page.getByTestId('ip-address')).toContainText('localhost');
  await expect(page.getByTestId('proxy-url-span')).toContainText('localhost');
  await expect(page.getByTestId('proxy-port-span')).toContainText('1883');
  await expect(page.getByTestId('proxy-username-span')).toContainText(
    'username_42',
  );
  await expect(page.getByTestId('dhcp-toggle')).toBeTruthy();

  await page.getByTestId('aimodel_tab').click();

  await expect(page.getByTestId('model-id')).toContainText('000000');
  await expect(page.getByTestId('model-version')).toContainText('0100');
  await expect(page.getByTestId('converter-version')).toContainText('030800');
});
