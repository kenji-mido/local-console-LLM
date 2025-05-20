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

import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { Component, Inject, OnDestroy } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { TextInputComponent } from '@app/layout/components/text-input/text-input.component';
import {
  UserPromptDialog,
  UserPromptDialogData,
} from '@app/layout/dialogs/user-prompt/user-prompt.dialog';

export interface UserPromptNameDialogData extends UserPromptDialogData {
  deviceName: string;
}

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
    deviceName: new FormControl(),
  });

  deviceName: string | null = null;
  isDeviceNameUpdated = false;

  constructor(
    public dialogRef: DialogRef<string | null>,
    @Inject(DIALOG_DATA) public data: UserPromptNameDialogData,
  ) {
    this.deviceName = data.deviceName;
  }

  ngOnDestroy() {
    if (this.isDeviceNameUpdated) this.dialogRef.close(this.deviceName);
  }

  onApply() {
    this.isDeviceNameUpdated = true;
    this.deviceName = this.inputs.value.deviceName;
  }
}
