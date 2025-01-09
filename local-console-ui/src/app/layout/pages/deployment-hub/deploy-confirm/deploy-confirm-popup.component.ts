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

import { CommonModule, formatDate } from '@angular/common';
import { Component, Inject, Input, LOCALE_ID } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import {
  MatDialogRef,
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogTitle,
} from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { DevicePipesModule } from '@app/core/device/device.pipes';
import { IconTextComponent } from '@app/core/file/icon-text/icon-text.component';

@Component({
  selector: 'app-deploy-confirm-popup',
  templateUrl: './deploy-confirm-popup.component.html',
  styleUrls: ['./deploy-confirm-popup.component.scss'],
  standalone: true,
  imports: [
    MatDialogTitle,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    CommonModule,
    FormsModule,
    IconTextComponent,
    DevicePipesModule,
  ],
})
export class DeployConfirmPopupComponent {
  mainChipFw: string = '';
  sensorChipFw: string = '';
  selectedDeviceName: string = '';

  constructor(
    public dialogRef: MatDialogRef<DeployConfirmPopupComponent>,

    @Inject(MAT_DIALOG_DATA) public data: any,
  ) {
    this.mainChipFw = data.mainChipFw;
    this.sensorChipFw = data.sensorChipFw;
    this.selectedDeviceName = data.selectedDeviceName;
  }
  onCancel(): void {
    this.dialogRef.close(false);
  }

  onDeploy(): void {
    this.dialogRef.close(true);
  }
}
