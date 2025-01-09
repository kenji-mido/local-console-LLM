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

import { DialogRef } from '@angular/cdk/dialog';
import { Component, OnDestroy } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { TextInputComponent } from '@app/layout/components/text-input/text-input.component';
import { UserPromptDialog } from '@app/layout/dialogs/user-prompt/user-prompt.dialog';

@Component({
  selector: 'app-user-prompt-name',
  styleUrls: ['./user-prompt-name.dialog.scss'],
  templateUrl: './user-prompt-name.dialog.html',
  standalone: true,
  imports: [
    UserPromptDialog,
    TextInputComponent,
    ReactiveFormsModule,
    MatIconModule,
  ],
})
export class UserPromptNameDialog implements OnDestroy {
  inputs = new FormGroup({
    device_name: new FormControl(),
  });

  device_name = null;

  constructor(public dialogRef: DialogRef<string | null>) {}

  ngOnDestroy() {
    this.dialogRef.close(this.device_name);
  }

  onApply() {
    this.device_name = this.inputs.value.device_name;
  }
}
