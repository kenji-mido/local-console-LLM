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

import { Device, DeviceList } from '@samplers/device';
import { LocalDevice } from '@app/core/device/device';
import test, { expect } from '@playwright/test';
import { firstValueFrom, Subject } from 'rxjs';
import { QRSamplers } from '@samplers/qr';
import { createDevice } from './interactions';

test('QR code is requested with the correct information from created device', async ({
  page,
}) => {
  const deviceList = DeviceList.sampleLocal();
  const firstPort = 1234;
  const secondPort = 2345;
  let receivedPort = new Subject<number | null>();
  // Given
  await page.route('**/devices?limit=500', async (route) => {
    await route.fulfill({ json: deviceList });
  });
  await page.route('**/provisioning/qrcode*', async (route) => {
    const url = new URL(route.request().url());
    const mqttPort = url.searchParams.get('mqtt_port');
    const port = mqttPort ? Number.parseInt(mqttPort) : null;
    receivedPort.next(port);
    await route.fulfill({ json: QRSamplers.sampleQrResponse() });
  });
  await page.route('http://localhost:8000/devices', async (route, request) => {
    if (request.method() === 'POST') {
      const body = JSON.parse(request.postData() || '{}');
      if (body.mqtt_port) {
        deviceList.devices.push(
          Device.sampleLocal(
            Device.sample(body.device_name, body.mqtt_port),
            body.mqtt_port,
          ),
        );
      }
      await route.fulfill({
        status: 200,
        json: {},
      });
    }
  });

  // When
  await page.goto('http://localhost:4200/provisioning-hub');
  const firstQrGenerationCall = firstValueFrom(receivedPort);
  await createDevice(page, 'device_one', firstPort);
  await page.getByTestId('qr-generate').click();

  // Then
  expect(await firstQrGenerationCall).toEqual(firstPort);

  // When
  await page.getByTestId('qr-close').click();
  const secondQrGenerationCall = firstValueFrom(receivedPort);
  await page.getByTestId('hub-mode-selector').getByTestId('option-0').click();
  await createDevice(page, 'device_two', secondPort);
  await page.getByTestId('qr-generate').click();

  // Then
  expect(await secondQrGenerationCall).toEqual(secondPort);
});
