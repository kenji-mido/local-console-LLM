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

import { TestInfo, type Page } from '@playwright/test';
import { setupMockServer } from '../../server-mock/server';

export async function websocketFixture(
  { page }: { page: Page },
  use: (value: number) => Promise<void>,
  testInfo: TestInfo,
) {
  const mockServer = setupMockServer({
    port: 0,
    setupHttp: false,
    setupWs: true,
  });
  const address = mockServer.server.address();
  if (!address || typeof address === 'string') {
    throw new Error('Failed to retrieve server address.');
  }
  const port = address.port;

  // Inject a script into the browser context before any page script runs.
  // This ensures that `window.API_URL` is available globally in the browser.
  // NOTE: `process.env` is a Node.js feature and is not accessible in the browser.
  await page.addInitScript((value) => {
    (window as any).API_URL = value;
  }, `http://localhost:${port}`);

  await use(port);
  mockServer.server.close();
}
