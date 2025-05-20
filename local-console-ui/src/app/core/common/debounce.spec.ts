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

import { debounce } from './debounce';

describe('debounce function', () => {
  jest.useFakeTimers();

  it('should debounce the function call', () => {
    const mockFn = jest.fn();
    const debouncedFn = debounce(mockFn, 1000);

    // call the debounced function
    debouncedFn('call1');
    debouncedFn('call2');
    debouncedFn('call3');

    // should not be called immediately
    expect(mockFn).not.toHaveBeenCalled();

    jest.advanceTimersByTime(1000);

    expect(mockFn).toHaveBeenCalledTimes(1);
    expect(mockFn).toHaveBeenCalledWith('call3');
  });

  it('should cancel the debounced function', () => {
    const mockFn = jest.fn();
    const debouncedFn = debounce(mockFn, 1000);

    // call the debounced function
    debouncedFn('call before cancel');

    // cancel the debounced function
    debouncedFn.cancel();

    jest.advanceTimersByTime(1000);

    expect(mockFn).not.toHaveBeenCalled();
  });

  it('should report running state correctly', () => {
    const mockFn = jest.fn();
    const debouncedFn = debounce(mockFn, 1000);

    // function should not be running
    expect(debouncedFn.running()).toBe(false);

    // call the debounced function and check the running state
    debouncedFn('call');
    expect(debouncedFn.running()).toBe(true);

    // fast-forward time and check running state after timeout
    jest.advanceTimersByTime(1000);
    expect(debouncedFn.running()).toBe(false);
  });
});
