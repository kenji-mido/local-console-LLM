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
  Inject,
  OnDestroy,
  Output,
} from '@angular/core';
import {
  ButtonComponent,
  Variant,
} from '../../components/button/button.component';
import { logError } from '../../../core/common/logging';
import { DIALOG_DATA, DialogModule, DialogRef } from '@angular/cdk/dialog';
import { DialogActionComponent } from '../../components/dialog-action/dialog-action.component';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { CommonModule } from '@angular/common';
import { MatDialogModule } from '@angular/material/dialog';
import { DialogCloseDirective } from '../dialog.close.directive';

export interface ActionButton {
  id: string;
  text: string;
  variant: Variant;
}

export interface UserPromptDialogData {
  title: string;
  message: string;
  type?: 'error' | 'warning' | 'success' | 'info';
  actionButtons?: ActionButton[];
  closeButtonText?: string;
}

@Component({
  selector: 'app-user-prompt',
  templateUrl: './user-prompt.dialog.html',
  styleUrls: ['./user-prompt.dialog.scss'],
  standalone: true,
  imports: [
    DialogActionComponent,
    ButtonComponent,
    MatProgressSpinnerModule,
    MatIconModule,
    CommonModule,
    DialogCloseDirective,
  ],
})
export class UserPromptDialog implements OnDestroy {
  @Output() isNotCancelled = new EventEmitter();

  theme = 'light';

  constructor(
    @Inject(DIALOG_DATA) public data: UserPromptDialogData,
    public dialogRef: DialogRef<ActionButton>,
  ) {}

  ngOnDestroy(): void {
    delete this.data.actionButtons;
  }

  async actionSubmit(action: ActionButton) {
    this.isNotCancelled.emit();
    try {
      this.dialogRef.close(action);
    } catch (err: any) {
      logError(err);
    }
  }
}
