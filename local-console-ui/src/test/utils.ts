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

export async function waitForExpect<T>(
  fn: () => T,
  timeout = 3000,
  interval = 50,
): Promise<T> {
  return new Promise<T>((done, fail) => {
    const startTime = Date.now();
    let lastError: any;

    function check() {
      try {
        done(fn());
      } catch (e) {
        lastError = e;
        if (Date.now() - startTime >= timeout) {
          fail(
            new Error(
              `waitForExpect: Condition not met within ${timeout}ms.\nLast error: ${lastError}`,
            ),
          );
        } else {
          setTimeout(check, interval);
        }
      }
    }

    check();
  });
}
