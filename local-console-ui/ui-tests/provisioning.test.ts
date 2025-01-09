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

import { LocalDevice } from '@app/core/device/device';
import { test, expect } from '@playwright/test';
import { DeviceList } from '@samplers/device';
import { createDevice } from './interactions';
const PROVISIONING_HUB = '/provisioning-hub';

const RED_PIXEL =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAQMAAAAl21bKAAAAA1BMVEXOFUPkK3CuAAAACklEQVQI12NgAAAAAgAB4iG8MwAAAABJRU5ErkJggg==';

test('Device is created', async ({ page }) => {
  const deviceList = DeviceList.sampleLocal();
  const firstDevice = <LocalDevice>deviceList.devices[0];
  // Given
  await page.route(
    `**/devices/${firstDevice.port}/modules/$system/command`,
    async (route) => {
      const json = {
        result: 'SUCCESS',
        command_response: { image: RED_PIXEL },
      };
      // To simulate load (and not stress the browser out requesting this all the time)
      setTimeout(route.fulfill.bind(route, { json }), 100);
    },
  );

  // When
  await page.goto('http://localhost:4200/provisioning-hub');
  await createDevice(page, firstDevice.device_name, firstDevice.port);
  await page.getByLabel('Start preview').isEnabled();
  await page.getByTestId('qr-generate').isEnabled();
  await page.getByText('1884', { exact: true }).isVisible();

  const response = await page.request.delete(
    `http://localhost:8000/devices/${firstDevice.port}`,
  );
  expect(response.status()).toBe(200);
});

test('Start stream preview', async ({ page }) => {
  // When
  await page.goto('http://localhost:4200/provisioning-hub');
  await page.getByTestId('option-1').click();
  await page.getByLabel('Start preview').isEnabled();
  await page.getByLabel('Start preview').click();

  // Then
  await expect(page.getByTestId('drawing')).toHaveClass(/streaming/);
  await expect(page.getByTestId('drawing-surface')).toBeVisible();
  const canvasLocator = page.getByTestId('drawing-surface');

  await expect
    .poll(async () => {
      return await canvasLocator.evaluate((element) => {
        const canvas = element as HTMLCanvasElement;
        const context = canvas.getContext('2d');
        if (!context) return false;
        const pixelBuffer = new Uint32Array(
          context.getImageData(0, 0, canvas.width, canvas.height).data.buffer,
        );

        return pixelBuffer.some((pixel) => pixel !== 0); // Returns true if canvas has drawing
      });
    })
    .toBe(true);
});

test('Streaming cannot start and user warned if device is unreachable', async ({
  page,
}) => {
  const deviceList = DeviceList.sampleLocal();
  const firstDevice = <LocalDevice>deviceList.devices[0];
  // Given
  await page.route('**/devices?limit=500', async (route) => {
    await route.fulfill({ json: deviceList });
  });
  await page.route('**/devices', async (route) => {
    await route.fulfill({ json: { result: 'SUCCESS' } });
  });
  await page.route(
    `**/devices/${firstDevice.device_id}/modules/$system/command`,
    async (route) => {
      route.fulfill({ json: { result: 'ERROR' }, status: 404 });
    },
  );

  // When
  await page.goto('http://localhost:4200/provisioning-hub');
  await createDevice(page, firstDevice.device_name, firstDevice.port);
  await page.getByTestId('option-1').click();
  await page.getByLabel('Start preview').isEnabled();
  await page.getByLabel('Start preview').click();

  // Then
  await expect(page.getByTestId('drawing')).not.toHaveClass(/streaming/);
  // and alert prompt is visible
  await expect(page.getByTestId('alert-dialog-title')).toContainText(
    'Failed to stream',
  );
  await expect(page.getByTestId('prompt-action-cancel')).toBeVisible();
});

test('Streaming is stopped and user warned if device is unreachable (4 consecutive times)', async ({
  page,
}) => {
  const deviceList = DeviceList.sampleLocal();
  const firstDevice = <LocalDevice>deviceList.devices[0];
  // Given
  await page.route('**/devices?limit=500', async (route) => {
    await route.fulfill({ json: deviceList });
  });
  await page.route('**/devices', async (route) => {
    await route.fulfill({ json: { result: 'SUCCESS' } });
  });

  await page.route(
    `**/devices/${firstDevice.device_id}/modules/$system/command`,
    async (route) => {
      route.fulfill({ json: { result: 'SUCCESS' } });
    },
  );

  await page.route(
    `**/images/devices/${firstDevice.device_id}/directories*`,
    async (route) => {
      route.fulfill({ json: { result: 'ERROR' } });
    },
  );

  // When
  await page.goto('http://localhost:4200/provisioning-hub');
  await createDevice(page, firstDevice.device_name, firstDevice.port);
  await page.getByTestId('option-1').click();
  await page.getByLabel('Start preview').isEnabled();
  await page.getByLabel('Start preview').click();

  // Then
  await expect(page.getByTestId('drawing')).not.toHaveClass(/streaming/, {
    timeout: 12000,
  });
  // and alert prompt is visible
  await expect(page.getByTestId('alert-dialog-title')).toContainText(
    'Preview stopped',
  );
  await expect(page.getByTestId('prompt-action-cancel')).toBeVisible();
});

test('Device registration should do nothing if form is not filled in properly', async ({
  page,
}) => {
  // Given
  const emptyList = DeviceList.sampleEmpty();
  const device_name = 'My device name';
  const mqtt_port = 12345;

  await page.route(
    'http://localhost:8000/devices?limit=500',
    async (route, request) => {
      if (request.method() === 'GET') {
        await route.fulfill({ json: emptyList });
      }
    },
  );

  // When
  await page.goto('http://localhost:4200/provisioning-hub');

  // Then
  await expect(page.getByTestId('device-register')).not.toBeEnabled();
  await page
    .getByTestId('device-register-name')
    .locator('input')
    .fill(device_name);
  await expect(page.getByTestId('device-register')).not.toBeEnabled();
  await page.getByTestId('device-register-name').locator('input').fill('');
  await page
    .getByTestId('device-register-port')
    .locator('input')
    .fill(mqtt_port.toString());
  await expect(page.getByTestId('device-register')).not.toBeEnabled();
});

test('Device form can be reset', async ({ page }) => {
  // Given
  const emptyList = DeviceList.sampleEmpty();
  const device_name = 'My device name';
  const mqtt_port = 12345;

  await page.route(
    'http://localhost:8000/devices?limit=500',
    async (route, request) => {
      if (request.method() === 'GET') {
        await route.fulfill({ json: emptyList });
      }
    },
  );

  // When
  await page.goto('http://localhost:4200/provisioning-hub');
  await page
    .getByTestId('device-register-name')
    .locator('input')
    .fill(device_name);
  await page
    .getByTestId('device-register-port')
    .locator('input')
    .fill(mqtt_port.toString());
  await page.getByTestId('device-reset').click();

  // Then
  expect(
    await page
      .getByTestId('device-register-name')
      .locator('input')
      .textContent(),
  ).not.toBe(device_name);
  expect(
    await page
      .getByTestId('device-register-port')
      .locator('input')
      .textContent(),
  ).not.toBe(mqtt_port.toString());
});

test('Device creation sends the correct form information', async ({ page }) => {
  // Given
  let getCallCount = 0;
  const deviceList = DeviceList.sampleLocal();
  deviceList.devices.splice(1, 2);
  const emptyList = DeviceList.sampleEmpty();
  const listResponses = [emptyList, deviceList];
  const device_name = 'Mydevicename';
  const mqtt_port = 12345;
  const device = <LocalDevice>deviceList.devices[0];
  device.device_name = device_name;
  device.port = mqtt_port;
  let sentName = '';
  let sentPort = 0;

  await page.route(
    'http://localhost:8000/devices?limit=500',
    async (route, request) => {
      if (request.method() === 'GET') {
        await route.fulfill({ json: listResponses[getCallCount] });
      }
    },
  );
  await page.route('**/devices', async (route) => {
    await route.fulfill({ json: { result: 'SUCCESS' } });
  });
  await page.route('http://localhost:8000/devices', async (route, request) => {
    if (request.method() === 'POST') {
      const body = JSON.parse(request.postData() || '{}');
      sentName = body.device_name;
      sentPort = body.mqtt_port;
      getCallCount++;
      await route.fulfill({
        status: 200,
      });
    }
  });

  // When
  await page.goto('http://localhost:4200/provisioning-hub');
  await createDevice(page, device_name, mqtt_port);

  // Then
  expect(sentName).toBe(device_name);
  expect(sentPort).toBe(mqtt_port);
});

test('QR form can be reset', async ({ page }) => {
  // When
  await page.goto('http://localhost:4200/provisioning-hub');
  await page.getByTestId('option-1').click();
  // Then
  //NTP parameter
  await page.getByPlaceholder('pool.ntp.org').fill('ntp');
  //IP address
  await page
    .locator('div')
    .filter({ hasText: /^Static IP$/ })
    .locator('div')
    .getByRole('img')
    .click();
  await page.getByPlaceholder('192.168.0.1').fill('mock_ip');
  //wifi ssid
  await page
    .locator('div')
    .filter({ hasText: /^Wi-Fi SSID$/ })
    .locator('div')
    .getByRole('img')
    .click();
  await page.getByPlaceholder('Enter Wi-Fi SSID').fill('wifi-ssid');
  //Reset
  await page.getByRole('button', { name: 'Reset' }).click();

  await expect(page.getByPlaceholder('pool.ntp.org')).toBeEmpty();
  await expect(page.getByPlaceholder('192.168.0.1')).toBeEmpty();
  await expect(page.getByPlaceholder('Enter Wi-Fi SSID')).toBeEmpty();
  //expect(page.getByRole('button', { name: 'Reset' })).toBeVisible();

  await expect(page.getByRole('button', { name: 'Reset' })).toBeDisabled();
});
