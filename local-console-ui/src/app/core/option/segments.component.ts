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

import {
  Component,
  EventEmitter,
  HostBinding,
  Input,
  Output,
} from '@angular/core';

export interface Segment {
  display: string;
  disabled?: boolean;
  tooltip?: string;
}

@Component({
  selector: 'app-segments',
  standalone: true,
  imports: [],
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
    @for (option of _options; track option.display; let index = $index) {
      <button
        [class]="option.display === value ? 'normal-hub-btn' : 'weak-hub-btn'"
        [attr.data-testid]="'option-' + index"
        (click)="valueChange.emit(option.display)"
        [disabled]="option.disabled || disabled"
        [attr.title]="option.tooltip || null"
      >
        {{ option.display }}
      </button>
    }
  `,
})
export class SegmentsComponent {
  protected _options: Segment[] = [];
  @Input() disabled: boolean = false;

  @Input() value: string = '';
  @Output() valueChange = new EventEmitter<string>();
  @HostBinding('attr.aria-disabled') get disabledAttr() {
    return this.disabled ? true : null;
  }
  @HostBinding('attr.role') role = 'radiogroup';

  @Input() set options(opts: Array<Segment | string>) {
    this._options = opts.map((opt) => {
      if (typeof opt === 'string') {
        return <Segment>{ display: opt };
      }
      return opt;
    });
  }
}
