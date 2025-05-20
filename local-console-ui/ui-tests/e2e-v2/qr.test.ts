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
import { firstValueFrom, Subject } from 'rxjs';
import { test } from '../e2e-fixtures/fixtures';
import { createDevice } from '../tools/interactions';

async function selectNicIfMultiple(page: Page): Promise<void> {
  let locator = page.getByText('Select Network Interface Card.');
  if (
    await locator
      .waitFor({ state: 'visible', timeout: 5000 })
      .then(() => true)
      .catch(() => false)
  ) {
    await page.getByTestId('facade').click();
    await expect(page.getByTestId('dropdown')).toBeVisible();
    await page.getByTestId('dropdown').getByTestId('option-0').click();
  }
}

test.describe(
  'Register QR Usage',
  {
    annotation: {
      type: 'Register QR Usage',
      description:
        'This test suit covers all E2E (FrontEnd + BackEnd) tests involving the QR used for registering new devices',
    },
  },
  () => {
    test(
      'QR code is requested with the correct information',
      {
        annotation: {
          type: 'QR code is requested with the correct information',
          description:
            'This test checks that when a QR is generated, the correct information from the device is included.',
        },
      },
      async ({ page, fixture }) => {
        const firstPort = 1234;
        const secondPort = 2345;
        let receivedPort = new Subject<number | null>();

        await page.route('**/provisioning/qrcode*', async (route) => {
          const url = new URL(route.request().url());
          const mqttPort = url.searchParams.get('mqtt_port');
          const port = mqttPort ? Number.parseInt(mqttPort) : null;
          receivedPort.next(port);
          await route.continue();
        });

        // When
        await page.goto('http://localhost:4200/provisioning-hub');
        const firstQrGenerationCall = firstValueFrom(receivedPort);
        await createDevice(page, 'device_one', firstPort);

        await selectNicIfMultiple(page);
        await page.getByTestId('qr-generate').click();

        // Then
        expect(
          await firstQrGenerationCall,
          'When calling the second QR generation, it should include the port of the first generated device.',
        ).toEqual(firstPort);

        // When
        await page.getByTestId('qr-close').click();
        const secondQrGenerationCall = firstValueFrom(receivedPort);
        await page
          .getByTestId('hub-mode-selector')
          .getByTestId('option-0')
          .click();
        await createDevice(page, 'device_two', secondPort);

        await selectNicIfMultiple(page);
        await page.getByTestId('qr-generate').click();

        // Then
        expect(
          await secondQrGenerationCall,
          'When calling the second QR generation, it should include the port of the second generated device.',
        ).toEqual(secondPort);

        const firstResponse = await page.request.delete(
          `http://localhost:8000/devices/${firstPort}`,
        );
        expect(
          firstResponse.status(),
          'A 200 status should be received when deleting the first device.',
        ).toBe(200);

        const secondResponse = await page.request.delete(
          `http://localhost:8000/devices/${secondPort}`,
        );
        expect(
          secondResponse.status(),
          'A 200 status should be received when deleting the second device.',
        ).toBe(200);
      },
    );
  },
);
