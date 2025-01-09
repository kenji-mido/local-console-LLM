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

import { PlaywrightTestConfig } from '@playwright/test';
import { register } from 'tsconfig-paths';

const tsConfig = require('./tsconfig.json');

register({
  baseUrl: tsConfig.compilerOptions.baseUrl,
  paths: tsConfig.compilerOptions.paths,
});

const config: PlaywrightTestConfig = {
  use: {
    // Use an environment variable, with a fallback to localhost
    baseURL: process.env['CONSOLE_BASE_URL'] || 'http://localhost:4200',
  },
  testDir: './ui-tests',
  outputDir: './ui-tests/report',
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
  reporter: [
    ['html', { open: 'never', outputFolder: './ui-tests/report' }],
    ['list'],
  ],
};
export default config;
