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

import { CommonModule } from '@angular/common';
import {
  Component,
  EventEmitter,
  HostBinding,
  Input,
  Output,
} from '@angular/core';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-number-spinner',
  templateUrl: './number-spinner.component.html',
  styleUrls: ['./number-spinner.component.scss'],
  standalone: true,
  imports: [FormsModule, CommonModule],
})
export class NumberSpinnerComponent {
  theme = 'light';

  @Input() label: string = '';
  @Input() data: number = 10;
  @Input() default: number = 10;
  @Input() min: number = 1;
  @Input() max: number = 20;
  @Input() step: number = 1;
  @Input() editableDisabled: boolean = true;
  @Input() minusPlusDisabled: boolean = true;
  @Input() width: number | 'auto' = 'auto';
  @Input() disabled = false;
  @Output() DataChange = new EventEmitter<number>();
  @HostBinding('attr.aria-disabled') get disabledAttr() {
    return this.disabled ? true : null;
  }
  @HostBinding('attr.role') role = 'spinbutton';

  // timers
  private resetTimer: any | null = null;
  private holdInterval: any | null = null;
  private holdTimeout: any | null = null;
  // intervals between actions
  readonly INVALID_INTERVAL = 1000;
  readonly HOLD_DELAY = 500;
  readonly HOLD_INTERVAL = 50;

  constructor() {}

  minus() {
    this.onInputChange(this.data - this.step);
  }

  plus() {
    this.onInputChange(this.data + this.step);
  }

  onInputChange(value: number | null) {
    if (this.resetTimer) {
      clearTimeout(this.resetTimer);
      this.resetTimer = null;
    }

    let resetValue = null;
    if (value === null) resetValue = this.default;
    else if (value < this.min) resetValue = this.min;
    else if (value > this.max) resetValue = this.max;

    if (resetValue !== null) {
      console.debug('Invalid value');
      this.resetTimer = setTimeout(() => {
        console.debug(`Setting expected value of ${resetValue}`);
        this.data = resetValue;
        this.DataChange.emit(this.data);
        this.resetTimer = null;
      }, this.INVALID_INTERVAL);
    } else {
      this.data = value!;
      this.DataChange.emit(this.data);
    }
  }

  startHoldAction(action: 'minus' | 'plus') {
    console.debug('Start hold action');
    // Prevent starting multiple hold actions
    if (this.holdTimeout || this.holdInterval) {
      return;
    }

    // Start the initial delay before repeating
    this.holdTimeout = setTimeout(() => {
      this.holdInterval = setInterval(() => {
        if (action === 'minus') {
          this.minus();
        } else if (action === 'plus') {
          this.plus();
        }
      }, this.HOLD_INTERVAL);
    }, this.HOLD_DELAY);
  }

  stopHoldAction() {
    console.debug('Stop hold action');
    clearTimeout(this.holdTimeout);
    clearInterval(this.holdInterval);
    this.holdTimeout = null;
    this.holdInterval = null;
  }
}
