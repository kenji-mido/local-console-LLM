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

import { effect, ModelSignal } from '@angular/core';

/**
 * Interface for SignalTracker that provides touched and reset functionality.
 */
export interface SignalTracker<T> {
  touch: () => void;
  touched: () => boolean;
  reset: () => void;
}

const øUNINIT: unique symbol = Symbol();

export function signalTracker<T>(signal: ModelSignal<T>): SignalTracker<T> {
  let lastValue: T | typeof øUNINIT = øUNINIT;
  let isTouched = false;

  function track(signal: ModelSignal<T>) {
    if (lastValue !== øUNINIT && lastValue !== signal()) {
      isTouched = true;
    }
    lastValue = signal();
  }

  effect(() => {
    track(signal);
  });

  return {
    touch: () => (isTouched = true),
    touched: () => isTouched,
    reset: () => (isTouched = false),
  };
}
