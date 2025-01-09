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
  Input,
  OnChanges,
  Output,
} from '@angular/core';
import { ControlContainer, FormGroupDirective } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { ReactiveFormsModule } from '@angular/forms';
import { Inject, OnDestroy } from '@angular/core';
import { MatInputModule } from '@angular/material/input';

export type InputType = 'text' | 'number' | 'email' | 'password';

@Component({
  selector: 'app-text-input',
  templateUrl: './text-input.component.html',
  styleUrls: ['./text-input.component.scss'],
  viewProviders: [
    {
      provide: ControlContainer,
      useExisting: FormGroupDirective,
    },
  ],
  standalone: true,
  imports: [
    CommonModule,
    MatFormFieldModule,
    MatIconModule,
    ReactiveFormsModule,
    MatInputModule,
  ],
})
export class TextInputComponent implements OnChanges {
  @Output() rightButtonClickedEvent = new EventEmitter();
  @Input() type: InputType = 'text';
  @Input() label?: string;
  @Input() formName: string = '';
  @Input() labelPos: 'top' | 'left' = 'top';
  @Input() rightButtonIcon?: string;
  @Input() placeholder: string = '';
  @Input() readOnly = false;
  @Input() maxLength: string = '1000';

  formFieldClass = '';

  constructor() {}

  ngOnChanges(): void {
    let cls = '';
    if (this.labelPos === 'left') cls = 'side-label';
    if (this.rightButtonIcon) cls += ' removable-input';
    this.formFieldClass = cls;
  }

  rightButtonClicked(): void {
    this.rightButtonClickedEvent.emit();
  }
}
