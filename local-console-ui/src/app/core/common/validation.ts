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

import { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';

export function assertNotEmpty<T>(value: T): asserts value is NonNullable<T> {
  if (value === undefined || value === null) {
    throw new Error(`${value} is not defined`);
  }
}

export function ipAddressValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    // TODO, verify the reg exp
    const pattern = new RegExp(
      '^(1\\d{2}|2[0-4]\\d|25[0-5]|[1-9]\\d|[1-9])\\.' +
        '(1\\d{2}|2[0-4]\\d|25[0-5]|[1-9]\\d|\\d)\\.' +
        '(1\\d{2}|2[0-4]\\d|25[0-5]|[1-9]\\d|\\d)\\.' +
        '(1\\d{2}|2[0-4]\\d|25[0-5]|[1-9]\\d|\\d)$',
    );
    const forbidden = pattern.test(control.value);
    return forbidden ? { ipv4Address: { value: control.value } } : null;
  };
}
