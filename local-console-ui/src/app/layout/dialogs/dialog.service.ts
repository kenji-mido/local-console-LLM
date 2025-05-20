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

import { Dialog, DialogRef } from '@angular/cdk/dialog';
import { ComponentType } from '@angular/cdk/portal';
import { Injectable } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { logError } from '../../core/common/logging';
import { ActionButton } from './user-prompt/action';
import {
  UserPromptDialog,
  UserPromptDialogData,
} from './user-prompt/user-prompt.dialog';

export type DialogClass<C> = ComponentType<C> & {
  cssClass?: string;
};

@Injectable({
  providedIn: 'root',
})
export class DialogService {
  constructor(private dialog: Dialog) {}

  async alert(
    title: string,
    message: string,
    type: UserPromptDialogData['type'] = 'error',
  ): Promise<ActionButton | undefined> {
    // TODO: The message should be a string, but in some cases it comes as HttpErrorResponse due to a design issue.
    // This check will no longer be necessary once the API error handling is moved to a common function
    if (message === '') return;
    if (typeof message !== 'string') {
      logError(
        new Error(
          `alert was given something other than string. Please extract your message from '${typeof message}'`,
        ),
      );
    }
    return this._open(UserPromptDialog, {
      title,
      message,
      type,
      closeButtonText: 'OK',
      showCancelButton: true,
      btnType: 'normal',
    });
  }

  async prompt(
    config: UserPromptDialogData,
    disableClose = true,
  ): Promise<ActionButton | undefined> {
    return this._open(UserPromptDialog, config, disableClose);
  }

  async _open<D, C>(
    dialog: DialogClass<C>,
    data?: unknown,
    disableClose = true,
  ): Promise<ActionButton | undefined> {
    const dialogRef = this.open(dialog, data, disableClose);
    try {
      const result = <ActionButton>await firstValueFrom(dialogRef.closed);
      if (result !== undefined && result !== null) {
        return result;
      }
    } catch {}
    return;
  }

  open<D, C>(
    dialog: DialogClass<C>,
    data?: unknown,
    disableClose = true,
  ): DialogRef<unknown, C> {
    return this.dialog.open(dialog, {
      panelClass: dialog.cssClass,
      data,
      disableClose: disableClose !== undefined ? disableClose : true,
    });
  }
}
