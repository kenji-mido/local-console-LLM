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
import { CommonModule } from '@angular/common';
import {
  Component,
  EventEmitter,
  Inject,
  OnDestroy,
  Output,
  TemplateRef,
} from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { logError } from '../../../core/common/logging';
import { DialogCloseDirective } from '../dialog.close.directive';
import { ActionButton, ButtonVariant } from './action';

export interface UserPromptDialogData {
  title: string;
  message: string | TemplateRef<any>;
  type?: 'error' | 'warning' | 'success' | 'info';
  actionButtons?: ActionButton[];
  closeButtonText?: string;
  showCancelButton: boolean;
  btnType?: ButtonVariant;
  context?: any;
}

@Component({
  selector: 'app-user-prompt',
  templateUrl: './user-prompt.dialog.html',
  styleUrls: ['./user-prompt.dialog.scss'],
  standalone: true,
  imports: [
    MatProgressSpinnerModule,
    MatIconModule,
    DialogCloseDirective,
    CommonModule,
  ],
})
export class UserPromptDialog implements OnDestroy {
  ButtonVariant = ButtonVariant;
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

  isTemplate(message: string | TemplateRef<any>): message is TemplateRef<any> {
    return message instanceof TemplateRef;
  }
}
