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
import {
  Component,
  Inject,
  LOCALE_ID,
  OnDestroy,
  TemplateRef,
  ViewChild,
} from '@angular/core';
import {
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import {
  DeployConfigApplyIn,
  DeployConfigsIn,
} from '@app/core/deployment/deployment';
import { EdgeAppService } from '@app/core/edge_app/edge_app.service';
import {
  FileInformationEvented,
  FileInputComponent,
} from '@app/core/file/file-input/file-input.component';
import { FilesService } from '@app/core/file/files.service';
import { IconTextComponent } from '@app/core/file/icon-text/icon-text.component';
import { TextInputComponent } from '../../components/text-input/text-input.component';
import { ToggleComponent } from '../../components/toggle/toggle.component';

import { DeploymentService } from '@app/core/deployment/deployment.service';
import { ModelService } from '@app/core/model/model.service';
import { DeploymentListComponent } from '@app/layout/components/deployment-list/deployment-list.component';

import { HttpErrorResponse } from '@angular/common/http';
import { LcDateTimePipe } from '@app/core/common/date';
import { Configuration } from '@app/core/device/configuration';
import {
  DeviceArchetype,
  DeviceStatus,
  LocalDevice,
} from '@app/core/device/device';
import { DevicePipesModule } from '@app/core/device/device.pipes';
import { DeviceService } from '@app/core/device/device.service';
import { InfotipDirective } from '@app/core/feedback/infotip.component';
import { FirmwareV2 } from '@app/core/firmware/firmware';
import { FirmwareService } from '@app/core/firmware/firmware.service';
import { DialogService } from '@app/layout/dialogs/dialog.service';
import { action } from '@app/layout/dialogs/user-prompt/action';
import { DeviceStatusBadgeComponent } from '../../../core/device/device-status/device-status-badge.component';
@Component({
  selector: 'app-deployment-hub',
  templateUrl: './deployment-hub.screen.html',
  styleUrls: ['./deployment-hub.screen.scss'],
  standalone: true,
  imports: [
    FileInputComponent,
    ToggleComponent,
    CommonModule,
    TextInputComponent,
    ReactiveFormsModule,
    IconTextComponent,
    DeploymentListComponent,
    InfotipDirective,
    LcDateTimePipe,
    DeviceStatusBadgeComponent,
    DevicePipesModule,
  ],
})
export class DeploymentHubScreen implements OnDestroy {
  @ViewChild('modelFile') modelFile!: FileInputComponent;
  @ViewChild('appFile') appFile!: FileInputComponent;
  @ViewChild('mainChipFile') mainChipFile!: FileInputComponent;
  @ViewChild('sensorChipFile') sensorChipFile!: FileInputComponent;
  @ViewChild('firmwareDeploymentConfirmation')
  firmwareDeploymentConfirmation!: TemplateRef<any>;

  DeviceArchetype = DeviceArchetype;
  theme = 'light';
  selectedDevice?: LocalDevice;
  selectedDeviceConfiguration: Configuration = {
    ai_model_file: null,
    module_file: null,
  };
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
  refresh_datetime = new Date();

  intervalMs = 5000;
  intervalHandler?: number;
  intervalStatusMs = 30000;
  intervalStatusHandler?: number;

  constructor(
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
    if (this.selectedDevice?.connection_state !== DeviceStatus.Connected) {
      return true; // Disabled
    }

    if (this.cam_fw_deploy && !this.bodyForm.controls['camFwControl'].valid) {
      return true; // Disabled
    }

    if (
      this.sensor_fw_deploy &&
      !this.bodyForm.controls['sensorFwControl'].valid
    ) {
      return true; // Disabled
    }

    // Anything is filled out, and valid
    if (
      this.cam_fw_deploy ||
      this.sensor_fw_deploy ||
      this.app_id ||
      this.model_id
    ) {
      return false; // Enabled
    }

    return true; // Disabled
  }

  async openDeviceSelectionDialog() {
    this.selectedDevice = await this.deviceService.askForDeviceSelection(
      this.selectedDevice,
    );

    if (this.selectedDevice) {
      const config = await this.deviceService.getConfiguration(
        this.selectedDevice!.device_id,
      );
      this.selectedDeviceConfiguration = config;
      console.debug(this.selectedDeviceConfiguration);

      await this.modelFile.sideloadFile(
        this.selectedDeviceConfiguration.ai_model_file ?? null,
      );
      await this.appFile.sideloadFile(
        this.selectedDeviceConfiguration.module_file ?? null,
      );
    }
  }

  async onModelSelection(fileHandle: FileInformationEvented) {
    let file_id: string | null = null;
    try {
      file_id = await this.filesService.createFiles(
        fileHandle,
        'converted_model',
      );
    } catch (e) {
      console.warn(e);
      this.modelFile.reset();
      this.model_id = null;
      return;
    }
    if (file_id === null) {
      this.modelFile.reset();
      this.model_id = null;
      return;
    }
    // No apparent reason to make model_id different than the file's hash
    this.model_id = await this.modelService.createModel(file_id, file_id);
    console.debug('Model created with id', this.model_id);

    if (!fileHandle.sideloaded) {
      await this.deviceService.patchConfiguration(
        this.selectedDevice!.device_id,
        { ai_model_file: fileHandle.path },
      );
    }
  }

  async onApplicationSelection(fileHandle: FileInformationEvented) {
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
      fileHandle.basename,
      this.app_id,
    );
    console.debug('App created with id', this.app_id);

    if (!fileHandle.sideloaded) {
      await this.deviceService.patchConfiguration(
        this.selectedDevice!.device_id,
        { module_file: fileHandle.path },
      );
    }
  }

  async onMainChipFwSelection(fileHandle: FileInformationEvented) {
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

  async onSensorChipFwSelection(fileHandle: FileInformationEvented) {
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
    }
    if (this.sensor_fw_id !== null) {
      deploy_config.edge_system_sw_package!.push({
        firmware_id: this.sensor_fw_id,
      });
    }
    console.debug('deploy_config:', deploy_config);

    if (this.cam_fw_deploy || this.sensor_fw_deploy) {
      const resultAction = await this.prompts.prompt({
        message: this.firmwareDeploymentConfirmation,
        title: 'Confirm Deployment',
        showCancelButton: false,
        actionButtons: [
          action.weak('cancel', 'Cancel'),
          action.normal('deploy', 'Deploy'),
        ],
      });

      if (resultAction?.id !== 'deploy') {
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
      device_ids: [this.selectedDevice.device_id],
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
    this.refresh_datetime = new Date();
    await this.deploymentService.loadDeployments();
  }

  async refreshDeviceStatus() {
    if (this.selectedDevice) {
      let device_info: LocalDevice = await this.deviceService.getDevice(
        this.selectedDevice.device_id,
        true,
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
