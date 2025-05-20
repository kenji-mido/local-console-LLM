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

import { environment } from '../../../environments/environment';

export class Environment {
  public getApiUrl() {
    let res = environment.apiUrl;
    try {
      // Check if `window.API_URL` is set (e.g., injected by Playwright or another script).
      // This allows dynamic API URL configuration at runtime, overriding the default value.
      const windowApiUrl = (window as any).API_URL;
      res = windowApiUrl || res;
    } catch {
      // If accessing `window` fails (e.g., in a non-browser environment), fallback to default.
    }
    return res;
  }
}
