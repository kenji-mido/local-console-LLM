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

import { Component, forwardRef, Input } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';

@Component({
  selector: 'app-segments',
  standalone: true,
  imports: [],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => SegmentsComponent),
      multi: true,
    },
  ],
  styles: `
    :host {
      display: flex;
    }
    button {
      margin: 0px;
    }

    button:not(:first-child) {
      border-top-left-radius: 0px;
      border-bottom-left-radius: 0px;
      border-left: none;
    }
    button:not(:last-child) {
      border-top-right-radius: 0px;
      border-bottom-right-radius: 0px;
    }
  `,
  template: `
    @for (option of options; track option; let index = $index) {
      <button
        [class]="option === value ? 'normal-hub-btn' : 'weak-hub-btn'"
        [attr.data-testid]="'option-' + index"
        (click)="onInput(option)"
        [disabled]="disabled"
      >
        {{ option }}
      </button>
    }
  `,
})
export class SegmentsComponent implements ControlValueAccessor {
  @Input() options: string[] = [];
  @Input() disabled: boolean = false;

  value: string = '';

  private onChange: (value: string) => void = () => {};

  private onTouched: () => void = () => {};

  onInput(value: string) {
    this.value = value;
    this.onChange(value);
    this.onTouched();
  }

  writeValue(value: string): void {
    this.value = value;
  }

  registerOnChange(fn: (value: string) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }
}
