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

test('Successful deployment test', async ({ page }) => {
  await page.goto('http://localhost:4200/deployment-hub');

  //select a device

  await page.getByTestId('select-device-to-deploy-button').click();

  const connectedRow = page.locator('tr:has-text("Connected")');

  await connectedRow.locator('input[type="radio"]').check();

  await page.getByRole('button', { name: 'Select' }).click();

  await expect(page.getByTestId('select-device-section')).toContainText(
    'Default',
  );

  //select AI model
  await loadFileIntoFileInput(
    page,
    'samples/model.pkg',
    page.getByTestId('model-selector'),
  );

  //select Application
  await loadFileIntoFileInput(
    page,
    'samples/app.bin',
    page.getByTestId('app-selector'),
  );

  await page.locator('app-toggle').getByRole('img').click();

  //select main chip fw
  await loadFileIntoFileInput(
    page,
    'samples/firmware.bin',
    page.getByTestId('chip-fw-selector'),
  );

  await page.locator('#mat-input-0').fill('1.0.0');

  //select sensor fw
  await loadFileIntoFileInput(
    page,
    'samples/firmware.fpk',
    page.getByTestId('sensor-fw-selector'),
  );

  await page.locator('#mat-input-1').fill('1.0.0');

  //deploy
  await page.getByRole('button', { name: 'Deploy' }).click();
  //confirm deploy
  await page.getByTestId('confirm-deploy').click();

  // TODO: this shouldn't be like this
  await expect(page.locator('td:nth-child(2) > span').first()).toContainText(
    'Default',
  );

  await expect(page.locator('tbody')).toContainText(
    DeploymentStatusOut.Success,
  );

  await expect(page.locator('tbody')).toContainText('app.bin');
  await expect(page.locator('tbody')).toContainText('model.pkg');
  await expect(page.locator('tbody')).toContainText('firmware.bin');
  await expect(page.locator('tbody')).toContainText('firmware.fpk');
  await expect(page.locator('tbody')).toContainText('Edge App');
  await expect(page.locator('tbody')).toContainText('Model');
  await expect(page.locator('tbody')).toContainText('Firmware');
});

async function loadFileIntoFileInput(
  page: Page,
  file: string,
  fileInput: Locator,
) {
  const fileName = file.split('/').pop() || 'invalid_file_name';
  const fileChooserPromise = page.waitForEvent('filechooser');
  await fileInput.getByTestId('actuator').click();
  const filechooser = await fileChooserPromise;
  await filechooser.setFiles(join(__dirname, file));
  await expect(
    fileInput.getByTestId('filename').getByTestId('text'),
  ).toContainText(fileName);
}
