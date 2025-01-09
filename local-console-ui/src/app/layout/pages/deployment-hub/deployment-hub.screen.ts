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
import {
  Component,
  Inject,
  LOCALE_ID,
  OnDestroy,
  ViewChild,
} from '@angular/core';
import { FileInputComponent } from '@app/core/file/file-input/file-input.component';
import { CardComponent } from '../../components/card/card.component';
import { ButtonComponent } from '../../components/button/button.component';
import { ToggleComponent } from '../../components/toggle/toggle.component';
import { TextInputComponent } from '../../components/text-input/text-input.component';
import {
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { IconTextComponent } from '@app/core/file/icon-text/icon-text.component';
import { MatDialog } from '@angular/material/dialog';
import { DeviceSelectionPopupComponent } from './device-selector/device-selection-popup.component';
import { DeployConfirmPopupComponent } from './deploy-confirm/deploy-confirm-popup.component';
import { FilesService } from '@app/core/file/files.service';
import { EdgeAppService } from '@app/core/edge_app/edge_app.service';
import {
  DeployConfigApplyIn,
  DeployConfigsIn,
} from '@app/core/deployment/deployment';

import { DeploymentService } from '@app/core/deployment/deployment.service';
import { ModelService } from '@app/core/model/model.service';
import { DeploymentListComponent } from '@app/layout/components/deployment-list/deployment-list.component';

import { FirmwareService } from '@app/core/firmware/firmware.service';
import { FirmwareV2, FirmwareType } from '@app/core/firmware/firmware';
import { DialogService } from '@app/layout/dialogs/dialog.service';
import { HttpErrorResponse } from '@angular/common/http';
import { DeviceStatusSvgPipe } from '@app/core/device/device.pipes';
import { DeviceService } from '@app/core/device/device.service';
import { DeviceStatus, DeviceV2 } from '@app/core/device/device';
import { lastValueFrom } from 'rxjs';
import { LocalDevice } from '@app/core/device/device';
import { InfotipDirective } from '@app/core/feedback/infotip.component';
@Component({
  selector: 'app-deployment-hub',
  templateUrl: './deployment-hub.screen.html',
  styleUrls: ['./deployment-hub.screen.scss'],
  standalone: true,
  imports: [
    FileInputComponent,
    CardComponent,
    ButtonComponent,
    ToggleComponent,
    CommonModule,
    TextInputComponent,
    ReactiveFormsModule,
    IconTextComponent,
    DeploymentListComponent,
    DeviceStatusSvgPipe,
    InfotipDirective,
  ],
})
export class DeploymentHubScreen implements OnDestroy {
  @ViewChild('modelFile') modelFile!: FileInputComponent;
  @ViewChild('appFile') appFile!: FileInputComponent;
  @ViewChild('mainChipFile') mainChipFile!: FileInputComponent;
  @ViewChild('sensorChipFile') sensorChipFile!: FileInputComponent;

  theme = 'light';
  selectedDevice?: LocalDevice;
  firmwareOptions: boolean = false;
  bodyForm = new FormGroup({
    camFwControl: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required],
    }),
    sensorFwControl: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required],
    }),
  });
  bodyStatus = new FormGroup({});
  app_id: string | null = null;
  model_id: string | null = null;
  sensor_fw_file_id: string | null = null;
  cam_fw_file_id: string | null = null;
  sensor_fw_id: string | null = null;
  cam_fw_id: string | null = null;
  cam_fw_deploy: boolean = false;
  sensor_fw_deploy: boolean = false;

  refreshIcon = 'images/light/reload_icon.svg';
  refresh_datetime = '';

  intervalMs = 5000;
  intervalHandler?: number;
  intervalStatusMs = 30000;
  intervalStatusHandler?: number;

  constructor(
    public dialog: MatDialog,
    private prompts: DialogService,
    private filesService: FilesService,
    private deviceService: DeviceService,
    private edgeAppService: EdgeAppService,
    private firmwareService: FirmwareService,
    private deploymentService: DeploymentService,
    private modelService: ModelService,
    @Inject(LOCALE_ID) private locale: string,
  ) {
    this.refresh();
    this.startInterval();
  }

  isDeployButtonDisabled(): boolean {
    const camFwVersionValid = this.bodyForm.controls['camFwControl'].valid;
    const sensorFwVersionValid =
      this.bodyForm.controls['sensorFwControl'].valid;

    const fwInfoCorrect: boolean =
      (camFwVersionValid &&
        this.cam_fw_deploy &&
        !sensorFwVersionValid &&
        !this.sensor_fw_deploy) ||
      (!camFwVersionValid &&
        !this.cam_fw_deploy &&
        sensorFwVersionValid &&
        this.sensor_fw_deploy) ||
      (camFwVersionValid &&
        this.cam_fw_deploy &&
        sensorFwVersionValid &&
        this.sensor_fw_deploy);

    const fwInfoEmpty: boolean =
      !camFwVersionValid &&
      !this.cam_fw_deploy &&
      !sensorFwVersionValid &&
      !this.sensor_fw_deploy;

    return !(
      (this.selectedDevice && fwInfoCorrect) ||
      (this.selectedDevice && (this.app_id || this.model_id) && fwInfoEmpty)
    );
  }

  openDeviceSelectionDialog(): void {
    const dialogRef = this.dialog.open(DeviceSelectionPopupComponent, {
      panelClass: 'custom-dialog-container',
      data: { selectedDevice: this.selectedDevice },
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        this.selectedDevice = result;
      }
    });
  }

  async onModelSelection(fileHandle: File) {
    let file_id: string | null = null;
    try {
      file_id = await this.filesService.createFiles(
        fileHandle,
        'converted_model',
      );
    } catch (e) {
      this.modelFile.reset();
      this.model_id = null;
      return;
    }
    if (file_id === null) {
      this.modelFile.reset();
      this.model_id = null;
      return;
    }
    let model_id = Math.floor(Math.random() * 10 ** 20).toString();
    this.model_id = await this.modelService.createModel(model_id, file_id);
    console.debug('Model created with id', this.model_id);
  }

  async onApplicationSelection(fileHandle: File) {
    console.debug('onApplicationSelection');
    try {
      this.app_id = await this.filesService.createFiles(
        fileHandle,
        'edge_app_dtdl',
      );
    } catch (e) {
      this.appFile.reset();
      this.app_id = null;
      return;
    }
    if (this.app_id === null) {
      this.appFile.reset();
      this.app_id = null;
      return;
    }
    this.app_id = await this.edgeAppService.createEdgeApp(
      fileHandle.name,
      this.app_id,
    );
    console.debug('App created with id', this.app_id);
  }

  async onMainChipFwSelection(fileHandle: File) {
    console.log('onMainChipFwSelection');
    try {
      this.cam_fw_file_id = await this.filesService.createFiles(
        fileHandle,
        'firmware',
      );
      this.cam_fw_deploy = true;
    } catch (e) {
      this.cam_fw_file_id = null;
      this.mainChipFile.reset();
    }
  }

  async onSensorChipFwSelection(fileHandle: File) {
    console.log('onSensorChipFwSelection');
    try {
      this.sensor_fw_file_id = await this.filesService.createFiles(
        fileHandle,
        'firmware',
      );
      this.sensor_fw_deploy = true;
    } catch (e) {
      this.sensor_fw_file_id = null;
      this.sensorChipFile.reset();
    }
  }

  async onDeploy() {
    let fwDeployConfirmData = {
      mainChipFw: '',
      sensorChipFw: '',
      selectedDeviceName: this.selectedDevice?.device_name,
    };
    if (!this.selectedDevice) {
      console.warn('Deploy action aborted: No device port selected.');
      return;
    }

    if (
      this.cam_fw_file_id !== null &&
      this.cam_fw_file_id !== this.cam_fw_id
    ) {
      console.debug('Posting application fw', this.cam_fw_file_id);
      const app_firmware_payload: FirmwareV2 = {
        firmware_type: 'ApFw',
        file_id: this.cam_fw_file_id,
        version: this.bodyForm.controls['camFwControl'].value,
      };
      this.cam_fw_id =
        await this.firmwareService.createFirmwareV2(app_firmware_payload);
    }

    if (
      this.sensor_fw_file_id !== null &&
      this.sensor_fw_file_id !== this.sensor_fw_id
    ) {
      console.debug('Posting sensor fw', this.sensor_fw_file_id);
      const sensor_firmware_payload: FirmwareV2 = {
        firmware_type: 'SensorFw',
        file_id: this.sensor_fw_file_id,
        version: this.bodyForm.controls['sensorFwControl'].value,
      };
      this.sensor_fw_id = await this.firmwareService.createFirmwareV2(
        sensor_firmware_payload,
      );
    }

    console.log(
      'onDeploy: app_id',
      this.app_id,
      'model_id',
      this.model_id,
      'cam_fw_id',
      this.cam_fw_id,
      'sensor_fw_id',
      this.sensor_fw_id,
    );
    let deploy_config: DeployConfigsIn = {
      config_id: Math.floor(Math.random() * 10 ** 20).toString(),
      edge_system_sw_package: [],
    };
    if (this.app_id !== null) {
      deploy_config.edge_apps = [
        {
          edge_app_package_id: this.app_id,
          app_name: '',
          app_version: '',
        },
      ];
    }
    if (this.model_id !== null) {
      deploy_config.models = [
        {
          model_id: this.model_id,
          model_version_number: '',
        },
      ];
    }
    if (this.cam_fw_id !== null) {
      deploy_config.edge_system_sw_package!.push({
        firmware_id: this.cam_fw_id,
      });
      fwDeployConfirmData.mainChipFw =
        this.bodyForm.controls['camFwControl'].value;
    }
    if (this.sensor_fw_id !== null) {
      deploy_config.edge_system_sw_package!.push({
        firmware_id: this.sensor_fw_id,
      });
      fwDeployConfirmData.sensorChipFw =
        this.bodyForm.controls['sensorFwControl'].value;
    }
    console.debug('deploy_config:', deploy_config);

    if (this.cam_fw_deploy || this.sensor_fw_deploy) {
      const dialogRef = this.dialog.open(DeployConfirmPopupComponent, {
        panelClass: 'custom-dialog-container',
        data: fwDeployConfirmData,
      });

      const deploy_confirmation = await lastValueFrom(dialogRef.afterClosed());
      if (!deploy_confirmation) {
        return;
      }
    }
    let result =
      await this.deploymentService.createDeploymentConfigV2(deploy_config);
    if (!result || result.result !== 'SUCCESS') {
      console.warn('Error while creating deployment config:', result);
      return;
    }
    let apply_deploy_config: DeployConfigApplyIn = {
      device_ids: [this.selectedDevice.port.toString()],
      description: 'placeholder',
    };
    try {
      result = await this.deploymentService.deployByConfigurationV2(
        deploy_config.config_id!,
        apply_deploy_config,
      );
    } catch (error) {
      console.log(error);
      var message =
        'Error while starting deployment. Please retry in a few seconds. A deployment might be already running.';
      if (error instanceof HttpErrorResponse) {
        const httpError = error as HttpErrorResponse;
        message = error.error.message;
      }
      this.prompts.alert('Deployment failed', message, 'warning');
    }

    if (!result || result.result !== 'SUCCESS') {
      console.warn('Error while applying deployment:', result);
    }
    this.refresh();
  }

  async refresh() {
    this.refresh_datetime = formatDate(
      new Date(),
      'yy.MM.dd HH:mm:ss',
      this.locale,
    );
    await this.deploymentService.loadDeployments();
  }

  async refreshDeviceStatus() {
    if (this.selectedDevice) {
      let device_info: DeviceV2 = await this.deviceService.getDeviceV2(
        this.selectedDevice.device_id,
      );
      this.selectedDevice.connection_state = device_info.connection_state;
    }
  }

  async reset() {
    // Reset IDs
    this.app_id = null;
    this.model_id = null;

    // Reset model and app file selector component
    await this.appFile.reset();
    await this.modelFile.reset();
    // The *ngIf directive destroys the components when 'firmwareOptions' is false,
    // and creates new instances when it's true, resetting their state.
    this.firmwareOptions = false;
    this.resetFirmwareOptions();
  }

  resetFirmwareOptions() {
    // Reset IDs
    this.cam_fw_file_id = null;
    this.cam_fw_id = null;
    this.sensor_fw_file_id = null;
    this.sensor_fw_id = null;
    this.cam_fw_deploy = false;
    this.sensor_fw_deploy = false;

    this.bodyForm.reset();
  }

  private startInterval() {
    if (!this.intervalHandler) {
      this.intervalHandler = window.setInterval(
        () => this.refresh(),
        this.intervalMs,
      );
    }
    if (!this.intervalStatusHandler) {
      this.intervalStatusHandler = window.setInterval(
        () => this.refreshDeviceStatus(),
        this.intervalStatusMs,
      );
    }
  }

  private stopInterval() {
    if (this.intervalHandler) {
      clearInterval(this.intervalHandler);
      this.intervalHandler = undefined;
    }
    if (this.intervalStatusHandler) {
      clearInterval(this.intervalStatusHandler);
      this.intervalStatusHandler = undefined;
    }
  }

  ngOnDestroy() {
    this.stopInterval();
  }

  protected readonly DeviceStatus = DeviceStatus;
}
