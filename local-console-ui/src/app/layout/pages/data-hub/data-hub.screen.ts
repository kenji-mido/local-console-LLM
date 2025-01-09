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

import { Component, inject, ViewChild } from '@angular/core';
import { MatSelectModule } from '@angular/material/select';
import { FormsModule } from '@angular/forms';
import { FileInputComponent } from '../../../core/file/file-input/file-input.component';
import { IconTextComponent } from '../../../core/file/icon-text/icon-text.component';
import { DeviceSelectionPopupComponent } from '../deployment-hub/device-selector/device-selection-popup.component';
import { MatDialog } from '@angular/material/dialog';
import {
  DeviceFrame,
  LocalDevice,
  UpdateModuleConfigurationPayloadV2,
} from '@app/core/device/device';
import { firstValueFrom } from 'rxjs';
import { DeviceService } from '@app/core/device/device.service';
import { FolderPickerComponent } from '../../../core/file/folder-path-input/folder-picker.component';
import { Classification, Detection, Mode } from '@app/core/inference/inference';
import { NumberSpinnerComponent } from '@app/layout/components/number-spinner/number-spinner.component';
import { Configuration } from '@app/core/device/configuration';
import { TextInputComponent } from '../../components/text-input/text-input.component';
import { DeviceVisualizerComponent } from '../../../core/device/device-visualizer/device-visualizer.component';
import { RoiDisplayComponent } from '../../../core/device/roi-display/roi-display.component';
import { OperationModeType } from './data-hub';
import { InferenceDisplayComponent } from '../../../core/inference/inference-display/inference-display.component';
import { CommonModule } from '@angular/common';
import { DialogService } from '@app/layout/dialogs/dialog.service';
import { InfotipDirective } from '@app/core/feedback/infotip.component';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ToastComponent } from '@app/layout/components/toast/toast';

const MODULE_ID = 'node';

export interface LabelsStored {
  labels: string[];
  applied: boolean;
}

@Component({
  selector: 'app-data-hub',
  templateUrl: './data-hub.screen.html',
  styleUrls: ['./data-hub.screen.scss'],
  standalone: true,
  imports: [
    MatSelectModule,
    FormsModule,
    FileInputComponent,
    IconTextComponent,
    InfotipDirective,
    FolderPickerComponent,
    NumberSpinnerComponent,
    TextInputComponent,
    DeviceVisualizerComponent,
    RoiDisplayComponent,
    InferenceDisplayComponent,
    CommonModule,
  ],
})
export class DataHubScreen {
  Mode = Mode;

  operationMode: OperationModeType = 'classification';
  selectedDevice?: LocalDevice;
  selectedDeviceConfiguration: Configuration = {
    vapp_type: 'classification',
    size: 100,
    inference_dir_path: null,
    image_dir_path: null,
  };
  pplParameters: string | null = null;
  labels: LabelsStored = { labels: [], applied: false };
  stop?: Function;
  inference?: Classification | Detection;

  @ViewChild(DeviceVisualizerComponent) visualizer?: DeviceVisualizerComponent;
  @ViewChild('paramsFile') paramsFile!: FileInputComponent;
  @ViewChild('modelFile') labelsFile!: FileInputComponent;

  public snackBar = inject(MatSnackBar);

  constructor(
    public dialog: MatDialog,
    private deviceService: DeviceService,
    private prompts: DialogService,
  ) {}

  checkLettersSpaces(strings: string[]): boolean {
    const regex = /^[a-zA-Z0-9_]+$/; // Matches only letters, numbers, and underscores
    return strings.every((str) => regex.test(str) && str.length > 0); //Max number of chars is 20 and can not be empty
  }

  checkCharsLength(strings: string[]): boolean {
    return strings.some((str) => str.length >= 20); //If number of chars is >20
  }

  cleanTrailingBlanks(strings: string[]): string[] {
    let lastIndex = strings.length - 1;

    const trimmedStrings = strings.map((str) => str.trim());
    // Find the last non-empty string
    while (lastIndex >= 0 && trimmedStrings[lastIndex] === '') {
      lastIndex--;
    }

    // Return a new array up to the last non-empty string
    return trimmedStrings.slice(0, lastIndex + 1);
  }

  async onLabelsSelected(labelsFile: File) {
    let labels = await labelsFile.text();
    const labels_arr: string[] = this.cleanTrailingBlanks(labels.split('\n'));

    if (!this.checkLettersSpaces(labels_arr)) {
      const labels_error: string = `Labels can only contain letters, numbers and underscores.
         There must be no blank lines between labels`;
      await this.prompts.alert('Labels are incorrect', labels_error);
      this.labels.labels = [];
      this.labelsFile.reset();
    } else {
      if (this.checkCharsLength(labels_arr)) {
        const result = await this.prompts.prompt({
          message: `Some of the loaded labels have more than 20 characters, which may impact readability.
            Are you sure you want to use these labels? `,
          title: 'Labels are too long',
          actionButtons: [{ id: 'ok', text: 'OK', variant: 'secondary' }],
          type: 'warning',
        });
        if (result === undefined) {
          return;
        }
      }
      this.labels.labels = labels_arr;
    }
  }

  async onPPLFileSelected(paramsFile: File) {
    let params = await paramsFile.text();
    try {
      this.pplParameters = JSON.parse(params);
    } catch (e) {
      console.error('File is not JSON');
      this.paramsFile.reset();
      this.pplParameters = null;
      const labels_error: string = `PPL Parameters file must be a valid JSON file, with one entry per parameter`;
      await this.prompts.alert('PPL Parameters are incorrect', labels_error);
    }
  }

  async onApply() {
    if (this.pplParameters) {
      const payload = <UpdateModuleConfigurationPayloadV2>{
        property: {
          configuration: {
            PPL_Parameters: this.pplParameters,
          },
        },
      };

      await this.deviceService.updateModuleConfigurationV2(
        this.selectedDevice!.device_id,
        MODULE_ID,
        payload,
      );
    }

    if (this.operationMode !== 'image')
      this.selectedDeviceConfiguration.vapp_type = this.operationMode;
    await this.deviceService.patchConfiguration(
      this.selectedDevice!.device_id,
      this.selectedDeviceConfiguration,
    );

    if (this.labels.labels.length > 0) this.labels.applied = true;

    this.snackBar.openFromComponent(ToastComponent, {
      data: {
        message: 'Configuration Applied',
        panelClass: 'success-snackbar',
      },
      duration: 3000,
    });
  }

  async openDeviceSelectionDialog() {
    const dialogRef = this.dialog.open(DeviceSelectionPopupComponent, {
      panelClass: 'custom-dialog-container',
      data: { selectedDevice: this.selectedDevice?.device_name },
    });

    this.selectedDevice = await firstValueFrom(dialogRef.afterClosed());
    // TODO: error handling
    const config = await this.deviceService.getConfiguration(
      this.selectedDevice!.device_id,
    );
    const current_vapp_type = this.selectedDeviceConfiguration.vapp_type;
    this.selectedDeviceConfiguration = config;
    if (!config.vapp_type)
      this.selectedDeviceConfiguration.vapp_type = current_vapp_type;
    console.debug(this.selectedDeviceConfiguration);
  }

  getModelName(model: OperationModeType) {
    if (model === 'classification') return 'Brain Builder Classifier';
    if (model === 'detection') return 'Brain Builder Detector';
    return '';
  }

  getModeName(model: OperationModeType) {
    if (model === 'image') return 'Image';
    return 'Image & Inference';
  }

  onFrameReceived(frame: DeviceFrame) {
    if (!frame.inference) return;
    this.inference = frame.inference;
  }

  onImagePathSelected(folderPath: string) {
    this.selectedDeviceConfiguration.image_dir_path = folderPath;
  }

  onInferencePathSelected(folderPath: string) {
    this.selectedDeviceConfiguration.inference_dir_path = folderPath;
  }

  onStorageSizeChange(val: number) {
    this.selectedDeviceConfiguration.size = val;
  }

  startStreaming() {
    if (!this.visualizer) return;
    this.visualizer.startPreview();
  }

  stopStreaming() {
    delete this.inference;
    this.visualizer?.stopInferenceStream();
  }
}
