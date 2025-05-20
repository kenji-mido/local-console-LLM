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

export type DeferredPromise<T> = Promise<T> & {
  resolve: (value: T | PromiseLike<T>) => void;
  reject: (reason?: any) => void;
};

export function defer<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason?: any) => void;

  const deferred = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  }) as DeferredPromise<T>;
  deferred.resolve = resolve;
  deferred.reject = reject;

  return deferred;
}
