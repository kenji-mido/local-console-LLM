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

import { Signal, signal, WritableSignal } from '@angular/core';

export class AsyncStateManager<T, D> {
  private _data: WritableSignal<T | D>;
  private _loading: WritableSignal<boolean>;
  private _error: WritableSignal<string | null>;

  constructor(defaultValue = null as D) {
    this._data = signal(defaultValue);
    this._loading = signal(false);
    this._error = signal(null);
  }

  get data(): Signal<T | D> {
    return this._data.asReadonly();
  }

  get loading(): Signal<boolean> {
    return this._loading.asReadonly();
  }

  get error(): Signal<string | null> {
    return this._error.asReadonly();
  }

  capture(promise: Promise<T>): void {
    this._loading.set(true);
    this._error.set(null);

    promise
      .then((result) => {
        this._data.set(result);
      })
      .catch((err) => {
        this._error.set(err instanceof Error ? err.message : 'Unknown error');
        console.error('Error while waiting for async completion', err);
      })
      .finally(() => {
        this._loading.set(false);
      });
  }
}

export function asyncState<T>(defaultValue: null): AsyncStateManager<T, null>;
export function asyncState<T>(defaultValue?: T): AsyncStateManager<T, T>;
export function asyncState<T>(defaultValue?: T | null) {
  if (defaultValue === null) {
    return new AsyncStateManager<T, null>(null);
  } else {
    return new AsyncStateManager<T, T>(defaultValue as T);
  }
}
