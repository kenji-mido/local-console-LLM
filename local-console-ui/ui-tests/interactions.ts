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

import { expect, Page } from '@playwright/test';

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
}
