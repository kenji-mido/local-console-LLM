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
import { Component, Input, OnInit } from '@angular/core';
import {
  ControlContainer,
  FormGroupDirective,
  ReactiveFormsModule,
} from '@angular/forms';
import { MatRadioModule } from '@angular/material/radio';

export interface Options {
  name: string;
  value: string;
}

@Component({
  selector: 'app-radio-button',
  templateUrl: './radio-button.component.html',
  styleUrls: ['./radio-button.component.scss'],
  viewProviders: [
    {
      provide: ControlContainer,
      useExisting: FormGroupDirective,
    },
  ],
  standalone: true,
  imports: [MatRadioModule, ReactiveFormsModule, CommonModule],
})
export class RadioButtonComponent implements OnInit {
  @Input() label?: string;
  @Input() labelPos: 'top' | 'left' = 'top';
  @Input() labelWidth: string = '';
  @Input() optionsDirection: 'row' | 'column' = 'row';
  @Input() formName: string = '';
  @Input() options: Options[] = [];
  @Input() disabled: boolean = false;

  labelDirection = '';

  constructor() {}

  ngOnInit(): void {
    this.labelDirection = `direction-${
      this.labelPos === 'top' ? 'column' : 'row'
    }`;
  }
}
