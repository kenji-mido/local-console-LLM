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

import { expect, type Page } from '@playwright/test';
import {
  DeviceManager,
  MockedDevice,
  RealDevice,
} from '../e2e-fixtures/devices';

export async function checkDetectionInf(device: DeviceManager, rows: string[]) {
  if (device instanceof MockedDevice) {
    // Get the expected inference data (see comment block above for its origin)
    const objTest = JSON.parse(
      '{"perception": {"object_detection_list": [{"class_id": 0, "bounding_box_type": "BoundingBox2d", "bounding_box": {"left": 263, "top": 121, "right": 300, "bottom": 175}, "score": 33.59}]}}',
    );
    // Ensure they match
    expect(JSON.parse(rows.join(''))).toMatchObject(objTest);
  } else if (device instanceof RealDevice) {
    const regex = /^\{  \"perception\": \{    \"object_detection_list\":/;
    // Ensure it contains the same format
    expect(rows.join('')).toEqual(expect.stringMatching(regex));
  }
}

export async function checkClassificationInf(
  device: DeviceManager,
  rows: string[],
) {
  if (device instanceof MockedDevice) {
    // Get the expected inference data (see comment block above for its origin)
    const objTest = JSON.parse(
      '{"perception": {"classification_list": [{"class_id": 3, "score": 35.16}, {"class_id": 1, "score": 21.48}, {"class_id": 4, "score": 18.75}, {"class_id": 0, "score": 16.8}, {"class_id": 2, "score": 7.81}]}}',
    );
    // Ensure they match
    expect(JSON.parse(rows.join(''))).toMatchObject(objTest);
  } else if (device instanceof RealDevice) {
    const regex = /^\{  \"perception\": \{    \"classification_list\":/;
    // Ensure it contains the same format
    expect(rows.join('')).toEqual(expect.stringMatching(regex));
  }
}

export async function checkDeviceTabs(
  page: Page,
  device: DeviceManager,
  host: string,
) {
  await expect(
    page.getByTestId('sensor'),
    "The Sensor value should be 'IMX500'.",
  ).toContainText('IMX500');
  await expect(
    page.getByTestId('main_chip'),
    'The Main Chip value should not be empty.',
  ).not.toBeEmpty();
  await expect(
    page.getByTestId('sensor_fw_main'),
    'The Sensor FW Main value should not be empty.',
  ).not.toBeEmpty();
  await expect(
    page.getByTestId('sensor_fw_loader'),
    'The Sensor FW Loader value should not be empty.',
  ).not.toBeEmpty();
  await expect(
    page.getByTestId('processing_state'),
    "The Processing State value should be 'Idle'.",
  ).toContainText('Idle');
  await expect(
    page.getByTestId('device_id'),
    "The Device ID value should be '1883'.",
  ).toContainText('1883');

  await page.getByTestId('network_tab').click();

  await expect(
    page.getByTestId('broker-port'),
    'The broker port used for the device.',
  ).toContainText('1883');
  await expect(
    page.getByTestId('broker-id'),
    'The broker host for the device.',
  ).toContainText(host);
  await expect(
    page.getByTestId('ntp-server'),
    "The NTP Server value should be 'pool.ntp.org'.",
  ).toContainText('pool.ntp.org');

  await expect(
    page.getByTestId('proxy-port-span'),
    'The Proxy Port value should not be empty.',
  ).not.toBeEmpty();

  if (device instanceof MockedDevice) {
    await expect(
      page.getByTestId('ip-address'),
      'The IP Address value should be Local Console host.',
    ).toContainText('localhost');
    await expect(
      page.getByTestId('proxy-url-span'),
      "The Proxy URL value should be 'localhost'.",
    ).toContainText('localhost');

    await expect(
      page.getByTestId('proxy-username-span'),
      "The Proxy Username value should be 'username_42'.",
    ).toContainText('username_42');
    await expect(
      page.getByTestId('dhcp-toggle'),
      'The DHCP toggle should be toggled.',
    ).toBeTruthy();
  }

  await page.getByTestId('aimodel_tab').click();

  await expect(
    page.getByTestId('model-id'),
    "The Model ID value should be '000000'.",
  ).toContainText('000000');
  await expect(
    page.getByTestId('model-version'),
    "The Model Version should be '0100'.",
  ).toContainText('0100');
  await expect(
    page.getByTestId('converter-version'),
    "The Converter Version should be '030800'.",
  ).toContainText('030800');
}
