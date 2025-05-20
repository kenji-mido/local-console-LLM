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

import { type FullConfig } from '@playwright/test';
import { promises as fs } from 'fs';
import { dirname, join, resolve } from 'path';

async function globalSetup(config: FullConfig) {
  /**
   * If VIRTUAL_ENV env var is not in the environment, read it from a file.
   * You can create this file by activating the virtualenv that has the
   * mocked-device installation, and do:
   *
   * $ echo $VIRTUAL_ENV > local-console-ui/ui-tests/venv-path
   *
   * This enables running and debugging your tests within your IDE.
   * You can change the values assigned to IP_ADDRESS, ECI_VERSION
   * and DEVICE_TYPE to run under the debugger and with real devices.
   */
  if (!process.env['VIRTUAL_ENV']) {
    const venvFile = resolve(
      join(dirname(config.configFile || '.'), 'ui-tests/venv-path'),
    );
    try {
      const venvPath = await fs.readFile(venvFile, 'utf8');
      process.env['VIRTUAL_ENV'] = venvPath.trim();
    } catch (error) {
      throw new Error('Could not init tests due to: ' + String(error));
    }
  }
  if (!process.env['DEVICE_TYPE']) {
    process.env['DEVICE_TYPE'] = 'mocked';
  }
  if (!process.env['IP_ADDRESS']) {
    process.env['IP_ADDRESS'] = 'localhost';
  }
  if (!process.env['ECI_VERSION']) {
    process.env['ECI_VERSION'] = '1';
  }
  let ECIfVersion = process.env['ECI_VERSION'];

  // Check parameters
  if (
    process.env['IP_ADDRESS'] === 'localhost' &&
    process.env['DEVICE_TYPE'] === 'real'
  ) {
    throw new Error(
      'Invalid configuration: A real device cannot use "localhost" as the IP address. Please provide a valid IP.',
    );
  }
  if (!['1', '2'].includes(ECIfVersion)) {
    throw new Error(
      `Invalid specified Edge-Cloud Interface version (${ECIfVersion}) for variable ECI_VERSION.`,
    );
  }
}

export default globalSetup;
