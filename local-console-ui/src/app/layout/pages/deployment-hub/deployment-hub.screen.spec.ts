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

import { ComponentFixture, fakeAsync, TestBed } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { DeploymentService } from '@app/core/deployment/deployment.service';
import { DeviceStatus } from '@app/core/device/device';
import { DeviceService } from '@app/core/device/device.service';
import { EdgeAppService } from '@app/core/edge_app/edge_app.service';
import { FileInputComponent } from '@app/core/file/file-input/file-input.component';
import { FilesService } from '@app/core/file/files.service';
import { FirmwareV2 } from '@app/core/firmware/firmware';
import { FirmwareService } from '@app/core/firmware/firmware.service';
import { ModelService } from '@app/core/model/model.service';
import { DialogService } from '@app/layout/dialogs/dialog.service';
import { action } from '@app/layout/dialogs/user-prompt/action';
import { Device } from '@samplers/device';
import { Files } from '@samplers/file';
import { of } from 'rxjs';
import { DeploymentHubScreen } from './deployment-hub.screen';

class MockFilesService {
  createFiles = jest.fn();
}

class MockEdgeAppService {
  createEdgeApp = jest.fn();
}

class MockFirmwareService {
  createFirmwareV2 = jest.fn();
}

class MockDeploymentService {
  createDeploymentConfigV2 = jest.fn();
  deployByConfigurationV2 = jest.fn();
  loadDeployments = jest.fn();
  deployment$ = of([]);
}

class MockModelService {
  createModel = jest.fn();
}

class MockDeviceService {
  getDevice = jest.fn();
  getConfiguration = jest.fn().mockResolvedValue({
    ai_model_file: null,
    module_file: null,
  });
  patchConfiguration = jest.fn();
  askForDeviceSelection = jest.fn();
}

class MockDialogService {
  prompt = jest.fn();
  alert = jest.fn();
}

describe('DeploymentHubScreen', () => {
  let component: DeploymentHubScreen;
  let fixture: ComponentFixture<DeploymentHubScreen>;
  let filesService: MockFilesService;
  let edgeAppService: MockEdgeAppService;
  let deploymentService: MockDeploymentService;
  let modelService: MockModelService;
  let firmwareService: MockFirmwareService;
  let deviceService: MockDeviceService;
  let dialogs: MockDialogService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ReactiveFormsModule, FileInputComponent, NoopAnimationsModule],
      providers: [
        { provide: DialogService, useClass: MockDialogService },
        { provide: FilesService, useClass: MockFilesService },
        { provide: EdgeAppService, useClass: MockEdgeAppService },
        { provide: DeploymentService, useClass: MockDeploymentService },
        { provide: ModelService, useClass: MockModelService },
        { provide: FirmwareService, useClass: MockFirmwareService },
        { provide: DeviceService, useClass: MockDeviceService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DeploymentHubScreen);
    component = fixture.componentInstance;
    filesService = TestBed.inject(FilesService) as unknown as MockFilesService;
    edgeAppService = TestBed.inject(
      EdgeAppService,
    ) as unknown as MockEdgeAppService;
    deploymentService = TestBed.inject(
      DeploymentService,
    ) as unknown as MockDeploymentService;
    modelService = TestBed.inject(ModelService) as unknown as MockModelService;
    firmwareService = TestBed.inject(
      FirmwareService,
    ) as unknown as MockFirmwareService;
    deviceService = TestBed.inject(
      DeviceService,
    ) as unknown as MockDeviceService;
    dialogs = TestBed.inject(DialogService) as unknown as MockDialogService;

    fixture.detectChanges();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should create the component', () => {
    expect(component).toBeTruthy();
  });

  describe('openDeviceSelectionDialog', () => {
    it('should open the device selection dialog and set selectedDevice and selectedDevicePort on close', async () => {
      const changedDevice = Device.sample({
        device_name: 'device-12345',
        device_id: '1883',
      });
      const initialDevice = Device.sample();
      component.selectedDevice = initialDevice;
      deviceService.askForDeviceSelection.mockResolvedValue(changedDevice);

      await component.openDeviceSelectionDialog();

      expect(deviceService.askForDeviceSelection).toHaveBeenCalledWith(
        initialDevice,
      );
      expect(component.selectedDevice).toBe(changedDevice);
    });

    it('should not change selectedDevice and selectedDevicePort if dialog is closed without result', fakeAsync(() => {
      const changedDevice = Device.sample({
        device_name: 'device-12345',
        device_id: '1883',
      });
      const expectedPort = '1884';
      component.selectedDevice = Device.sample({
        device_name: 'device123',
        device_id: '1884',
      });
      deviceService.askForDeviceSelection.mockResolvedValue(undefined);

      component.openDeviceSelectionDialog();

      expect(deviceService.askForDeviceSelection).toHaveBeenCalled();
      expect(component.selectedDevice.device_id).toBe(expectedPort.toString());
    }));
  });

  describe('onModelSelection', () => {
    it('should create model and set model_id', async () => {
      const mockFileHandle = Files.sample('model.bin');
      component.selectedDevice = Device.sample({
        device_name: 'device-12345',
        device_id: '1883',
      });
      filesService.createFiles.mockResolvedValue('file123');
      modelService.createModel.mockResolvedValue('model123');

      await component.onModelSelection(mockFileHandle);

      expect(filesService.createFiles).toHaveBeenCalledWith(
        mockFileHandle,
        'converted_model',
      );
      expect(modelService.createModel).toHaveBeenCalledWith(
        expect.any(String),
        'file123',
      );
      expect(component.model_id).toBe('model123');
    });

    it('should not set model_id if createFiles returns null', async () => {
      const mockFileHandle = Files.sample('model.bin');
      filesService.createFiles.mockResolvedValue(null);

      await component.onModelSelection(mockFileHandle);

      expect(filesService.createFiles).toHaveBeenCalledWith(
        mockFileHandle,
        'converted_model',
      );
      expect(modelService.createModel).not.toHaveBeenCalled();
      expect(component.model_id).toBeNull();
    });
  });

  describe('onApplicationSelection', () => {
    it('should create edge app and set app_id', async () => {
      const mockFileHandle = Files.sample('app.bin');
      component.selectedDevice = Device.sample({
        device_name: 'device-12345',
        device_id: '1883',
      });

      filesService.createFiles.mockResolvedValue('file456');
      edgeAppService.createEdgeApp.mockResolvedValue('app789');

      await component.onApplicationSelection(mockFileHandle);

      expect(filesService.createFiles).toHaveBeenCalledWith(
        mockFileHandle,
        'edge_app_dtdl',
      );
      expect(edgeAppService.createEdgeApp).toHaveBeenCalledWith(
        'app.bin',
        'file456',
      );
      expect(component.app_id).toBe('app789');
    });

    it('should not set app_id if createFiles returns null', async () => {
      const mockFileHandle = Files.sample('app.bin');
      filesService.createFiles.mockResolvedValue(null);

      await component.onApplicationSelection(mockFileHandle);

      expect(filesService.createFiles).toHaveBeenCalledWith(
        mockFileHandle,
        'edge_app_dtdl',
      );
      expect(edgeAppService.createEdgeApp).not.toHaveBeenCalled();
      expect(component.app_id).toBeNull();
    });
  });

  describe('onMainChipFwSelection', () => {
    it('should create sensor firmware and id', async () => {
      const mockFileHandle = Files.sample('fw.fpk');
      filesService.createFiles.mockResolvedValue('file789');

      await component.onMainChipFwSelection(mockFileHandle);

      expect(filesService.createFiles).toHaveBeenCalledWith(
        mockFileHandle,
        'firmware',
      );
      expect(component.cam_fw_file_id).toBe('file789');
      expect(component.cam_fw_deploy).toBe(true);
    });
  });

  describe('onSensorChipFwSelection', () => {
    it('should create sensor firmware and id', async () => {
      const mockFileHandle = Files.sample('fw.fpk');
      filesService.createFiles.mockResolvedValue('file910');
      firmwareService.createFirmwareV2.mockResolvedValue('file910');

      await component.onSensorChipFwSelection(mockFileHandle);

      expect(filesService.createFiles).toHaveBeenCalledWith(
        mockFileHandle,
        'firmware',
      );
      expect(component.sensor_fw_file_id).toBe('file910');
      expect(component.sensor_fw_deploy).toBe(true);
    });
  });

  describe('refreshDeviceStatus', () => {
    it('should update the selectedDeviceStatus', async () => {
      component.selectedDevice = Device.sample();
      component.selectedDevice.connection_state = DeviceStatus.Disconnected;
      const newStatus = DeviceStatus.Connected;
      const updatedDevice = Device.sample();
      updatedDevice.connection_state = newStatus;

      deviceService.getDevice.mockResolvedValue(updatedDevice);

      await component.refreshDeviceStatus();

      expect(deviceService.getDevice).toHaveBeenCalledWith(
        component.selectedDevice.device_id,
        true,
      );
      expect(component.selectedDevice.connection_state).toEqual(newStatus);
    });

    it('should not update the status if no device selected', async () => {
      component.selectedDevice = undefined;
      const newStatus = DeviceStatus.Connected;
      const updatedDevice = Device.sample();
      updatedDevice.connection_state = newStatus;

      deviceService.getDevice.mockResolvedValue(updatedDevice);

      await component.refreshDeviceStatus();

      expect(deviceService.getDevice).not.toHaveBeenCalled();
    });
  });

  describe('onDeploy', () => {
    it('should deploy successfully when all conditions are met', async () => {
      const port = 1883;
      component.selectedDevice = Device.sample({
        device_name: 'device-12345',
        device_id: '1883',
      });
      component.app_id = 'app123';
      component.model_id = 'model123';
      component.cam_fw_file_id = 'firmwarefile123';
      component.sensor_fw_file_id = 'firmwarefile456';
      component.cam_fw_deploy = true;
      component.sensor_fw_deploy = true;
      component.bodyForm.controls['camFwControl'].setValue('1.0.0');
      component.bodyForm.controls['sensorFwControl'].setValue('1.0.0');

      deploymentService.createDeploymentConfigV2.mockResolvedValue({
        result: 'SUCCESS',
        config_id: 'config123',
      });
      deploymentService.deployByConfigurationV2.mockResolvedValue({
        result: 'SUCCESS',
      });
      firmwareService.createFirmwareV2.mockResolvedValue('firmware123');
      dialogs.prompt.mockResolvedValue(action.normal('deploy', 'Deploy'));

      await component.onDeploy();

      const app_firmware_payload: FirmwareV2 = {
        firmware_type: 'ApFw',
        file_id: 'firmwarefile123',
        version: '1.0.0',
      };
      expect(firmwareService.createFirmwareV2).toHaveBeenCalledWith(
        app_firmware_payload,
      );
      expect(component.cam_fw_id).toBe('firmware123');

      const sensor_firmware_payload: FirmwareV2 = {
        firmware_type: 'SensorFw',
        file_id: 'firmwarefile456',
        version: '1.0.0',
      };
      expect(firmwareService.createFirmwareV2).toHaveBeenCalledWith(
        sensor_firmware_payload,
      );
      expect(component.sensor_fw_id).toBe('firmware123');

      expect(deploymentService.createDeploymentConfigV2).toHaveBeenCalledWith({
        config_id: expect.any(String),
        edge_apps: [
          {
            edge_app_package_id: 'app123',
            app_name: '',
            app_version: '',
          },
        ],
        edge_system_sw_package: [
          { firmware_id: 'firmware123' },
          { firmware_id: 'firmware123' },
        ],
        models: [
          {
            model_id: 'model123',
            model_version_number: '',
          },
        ],
      });

      expect(deploymentService.deployByConfigurationV2).toHaveBeenCalledWith(
        expect.any(String),
        {
          device_ids: [port.toString()],
          description: 'placeholder',
        },
      );
    });

    it('should not deploy if is not confirmed', async () => {
      component.selectedDevice = Device.sample({
        device_name: 'device-12345',
        device_id: '1883',
      });
      component.app_id = 'app123';
      component.model_id = 'model123';
      component.cam_fw_file_id = 'firmwarefile123';
      component.sensor_fw_file_id = 'firmwarefile456';
      component.bodyForm.controls['camFwControl'].setValue('1.0.0');
      component.bodyForm.controls['sensorFwControl'].setValue('1.0.0');
      component.cam_fw_deploy = true;
      component.sensor_fw_deploy = true;
      dialogs.prompt.mockResolvedValue(action.weak('cancel', 'Cancel'));
      firmwareService.createFirmwareV2.mockResolvedValue('firmware123');

      await component.onDeploy();

      const app_firmware_payload: FirmwareV2 = {
        firmware_type: 'ApFw',
        file_id: 'firmwarefile123',
        version: '1.0.0',
      };
      expect(firmwareService.createFirmwareV2).toHaveBeenCalledWith(
        app_firmware_payload,
      );
      expect(component.cam_fw_id).toBe('firmware123');

      const sensor_firmware_payload: FirmwareV2 = {
        firmware_type: 'SensorFw',
        file_id: 'firmwarefile456',
        version: '1.0.0',
      };
      expect(firmwareService.createFirmwareV2).toHaveBeenCalledWith(
        sensor_firmware_payload,
      );
      expect(component.sensor_fw_id).toBe('firmware123');

      expect(deploymentService.createDeploymentConfigV2).not.toHaveBeenCalled();

      expect(deploymentService.deployByConfigurationV2).not.toHaveBeenCalled();
    });

    it('should handle failure in applying deployment config', async () => {
      const port = 1883;
      component.selectedDevice = Device.sample({
        device_name: 'device-12345',
        device_id: '1883',
      });
      deploymentService.createDeploymentConfigV2.mockResolvedValue({
        result: 'SUCCESS',
        config_id: 'config123',
      });
      deploymentService.deployByConfigurationV2.mockResolvedValue({
        result: 'FAILURE',
      });
      const consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();

      await component.onDeploy();

      expect(deploymentService.createDeploymentConfigV2).toHaveBeenCalled();
      expect(deploymentService.deployByConfigurationV2).toHaveBeenCalledWith(
        expect.any(String),
        {
          device_ids: [port.toString()],
          description: 'placeholder',
        },
      );
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        'Error while applying deployment:',
        { result: 'FAILURE' },
      );

      consoleWarnSpy.mockRestore();
    });
  });

  describe('reset functionality', () => {
    let selectedDevice = 'Device1';
    let selectedDevicePort = '1883';

    beforeEach(() => {
      // set initial values different from default
      component.selectedDevice = Device.sample({
        device_name: selectedDevice,
        device_id: selectedDevicePort,
      });

      component.firmwareOptions = true;
      component.bodyForm.patchValue({
        camFwControl: '2.0.0',
        sensorFwControl: '2.0.0',
      });
      component.model_id = 'model_id';
      component.app_id = 'app_id';
      component.sensor_fw_file_id = 'sensor_fw_file_id';
      component.cam_fw_file_id = 'cam_fw_file_id';
      component.sensor_fw_id = 'sensor_fw_id';
      component.cam_fw_id = 'cam_fw_id';

      component.modelFile.reset = jest.fn();
      component.appFile.reset = jest.fn();
    });

    it('should reset all form controls, selections, and states', async () => {
      const mockResetFirmwareOptions = jest
        .spyOn(component, 'resetFirmwareOptions')
        .mockImplementation();
      await component.reset();

      expect(component.firmwareOptions).toBe(false);

      expect(component.app_id).toBeNull();
      expect(component.model_id).toBeNull();
      expect(mockResetFirmwareOptions).toHaveBeenCalled();
    });

    it('resetFirmwareOptions', async () => {
      component.resetFirmwareOptions();

      expect(component.bodyForm.controls['camFwControl'].value).toBe('');
      expect(component.bodyForm.controls['sensorFwControl'].value).toBe('');
      expect(component.sensor_fw_file_id).toBeNull();
      expect(component.cam_fw_file_id).toBeNull();
      expect(component.sensor_fw_id).toBeNull();
      expect(component.cam_fw_id).toBeNull();
    });
  });

  describe('isDeployButtonDisabled', () => {
    beforeEach(() => {
      component.selectedDevice = Device.sample();
      component.cam_fw_deploy = false;
      component.sensor_fw_deploy = false;
      component.bodyForm.controls['camFwControl'].setValue('');
      component.bodyForm.controls['sensorFwControl'].setValue('');
    });

    it('should return true if the device is not connected', () => {
      component.selectedDevice = Device.sample({
        connection_state: DeviceStatus.Disconnected,
      });
      expect(component.isDeployButtonDisabled()).toBe(true);
    });

    it('should return true if camFwControl is not valid and cam_fw_deploy is true', () => {
      component.selectedDevice = Device.sample();
      component.cam_fw_deploy = true;
      component.bodyForm.controls['camFwControl'].setValue(''); // invalid value
      expect(component.isDeployButtonDisabled()).toBe(true);
    });

    it('should return true if sensorFwControl is not valid and sensor_fw_deploy is true', () => {
      component.selectedDevice = Device.sample();
      component.sensor_fw_deploy = true;
      component.bodyForm.controls['sensorFwControl'].setValue(''); // invalid value
      expect(component.isDeployButtonDisabled()).toBe(true);
    });

    it('should return false if any of cam_fw_deploy, sensor_fw_deploy, app_id, or model_id are set', () => {
      component.selectedDevice = Device.sample();
      component.cam_fw_deploy = true;
      component.bodyForm.controls['camFwControl'].setValue('valid'); // valid value
      expect(component.isDeployButtonDisabled()).toBe(false);
    });

    it('should return true if no conditions are met', () => {
      component.selectedDevice = Device.sample();
      component.cam_fw_deploy = false;
      component.sensor_fw_deploy = false;
      component.app_id = null;
      component.model_id = null;
      expect(component.isDeployButtonDisabled()).toBe(true);
    });

    it('should return false if camFwControl is valid and cam_fw_deploy is true', () => {
      component.selectedDevice = Device.sample();
      component.cam_fw_deploy = true;
      component.bodyForm.controls['camFwControl'].setValue('valid');
      expect(component.isDeployButtonDisabled()).toBe(false);
    });

    it('should return false if sensorFwControl is valid and sensor_fw_deploy is true', () => {
      component.selectedDevice = Device.sample();
      component.sensor_fw_deploy = true;
      component.bodyForm.controls['sensorFwControl'].setValue('valid');
      expect(component.isDeployButtonDisabled()).toBe(false);
    });
  });
});
