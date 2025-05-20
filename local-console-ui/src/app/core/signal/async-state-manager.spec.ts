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

import { AsyncStateManager, asyncState } from './async-state-manager';

describe('AsyncStateManager', () => {
  let manager: AsyncStateManager<number, number>;

  beforeEach(() => {
    manager = asyncState<number>(0);
  });

  it('should initialize with default data', () => {
    expect(manager.data()).toBe(0);
    expect(manager.loading()).toBeFalsy();
    expect(manager.error()).toBeNull();
  });

  it('should set loading to true when capturing a promise', async () => {
    const promise = new Promise<number>((resolve) =>
      setTimeout(() => resolve(42), 100),
    );
    manager.capture(promise);

    expect(manager.loading()).toBeTruthy();
    expect(manager.data()).toBe(0); // Default value should remain until promise resolves

    await promise;

    expect(manager.loading()).toBeFalsy();
    expect(manager.data()).toBe(42); // The value should be updated once the promise resolves
    expect(manager.error()).toBeNull();
  });

  it('should update error when promise rejects', async () => {
    const promise = Promise.reject(new Error('Fetch failed'));
    manager.capture(promise);

    try {
      await promise;
    } catch {}

    expect(manager.data()).toBe(0); // Default remains unchanged
    expect(manager.loading()).toBeFalsy();
    expect(manager.error()).toBe('Fetch failed');
  });

  it('should handle non-error rejections gracefully', async () => {
    const promise = Promise.reject('Unknown error');
    manager.capture(promise);

    try {
      await promise;
    } catch {}

    expect(manager.data()).toBe(0); // Default remains unchanged
    expect(manager.loading()).toBeFalsy();
    expect(manager.error()).toBe('Unknown error');
  });

  it('should allow overlapping promises, updating data based on the latest fulfilled', async () => {
    const promise1 = new Promise<number>((resolve) =>
      setTimeout(() => resolve(10), 200),
    );
    const promise2 = new Promise<number>((resolve) =>
      setTimeout(() => resolve(20), 100),
    );

    manager.capture(promise1);
    manager.capture(promise2);

    expect(manager.loading()).toBeTruthy(); // Loading is true while promises are unresolved

    await promise2;
    expect(manager.data()).toBe(20); // The second promise fulfilled first
    expect(manager.loading()).toBeFalsy(); // Loading becomes false after the latest promise

    await promise1;
    expect(manager.data()).toBe(10); // The first promise fulfilled later and overwrote the state
  });

  it('should reset loading and error signals between captures', async () => {
    const promise = Promise.reject(new Error('Fetch failed'));
    manager.capture(promise);

    try {
      await promise;
    } catch {}

    expect(manager.error()).toBe('Fetch failed');
    expect(manager.loading()).toBeFalsy();

    const promise2 = Promise.resolve(42);
    manager.capture(promise2);

    expect(manager.loading()).toBeTruthy(); // Loading reset to true
    expect(manager.error()).toBeNull(); // Error reset to null

    await promise2;
    expect(manager.data()).toBe(42);
  });
});
