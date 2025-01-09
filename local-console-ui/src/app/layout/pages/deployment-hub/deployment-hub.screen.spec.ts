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

import { TestBed, ComponentFixture, fakeAsync } from '@angular/core/testing';
import { DeploymentHubScreen } from './deployment-hub.screen';
import { MatDialog } from '@angular/material/dialog';
import { FilesService } from '@app/core/file/files.service';
import { EdgeAppService } from '@app/core/edge_app/edge_app.service';
import { FirmwareService } from '@app/core/firmware/firmware.service';
import { FirmwareV2 } from '@app/core/firmware/firmware';
import { DeploymentService } from '@app/core/deployment/deployment.service';
import { ModelService } from '@app/core/model/model.service';
import { ReactiveFormsModule } from '@angular/forms';
import { Observable, of } from 'rxjs';
import { DeviceSelectionPopupComponent } from './device-selector/device-selection-popup.component';
import { Files } from '@samplers/file';
import { FileInputComponent } from '@app/core/file/file-input/file-input.component';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { DeviceService } from '@app/core/device/device.service';
import { DeviceStatus } from '@app/core/device/device';
import { Device } from '@samplers/device';

class MockMatDialog {
  afterCloseVal: boolean = true;
  open = jest
    .fn()
    .mockReturnValue({ afterClosed: () => of(this.afterCloseVal) });
}

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
  getDeviceV2 = jest.fn();
}

describe('DeploymentHubScreen', () => {
  let component: DeploymentHubScreen;
  let fixture: ComponentFixture<DeploymentHubScreen>;
  let dialog: MockMatDialog;
  let filesService: MockFilesService;
  let edgeAppService: MockEdgeAppService;
  let deploymentService: MockDeploymentService;
  let modelService: MockModelService;
  let firmwareService: MockFirmwareService;
  let deviceService: MockDeviceService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ReactiveFormsModule, FileInputComponent, NoopAnimationsModule],
      providers: [
        { provide: MatDialog, useClass: MockMatDialog },
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
    dialog = TestBed.inject(MatDialog) as unknown as MockMatDialog;
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

    fixture.detectChanges();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should create the component', () => {
    expect(component).toBeTruthy();
  });

  describe('openDeviceSelectionDialog', () => {
    it('should open the device selection dialog and set selectedDevice and selectedDevicePort on close', fakeAsync(() => {
      const changedDevice = Device.sampleLocal(Device.sample(), 1884);
      const initialDevice = Device.sampleLocal();
      component.selectedDevice = initialDevice;

      const mockDialogRef = {
        afterClosed: () => of(changedDevice),
      };
      dialog.open.mockReturnValue(mockDialogRef);

      component.openDeviceSelectionDialog();

      expect(dialog.open).toHaveBeenCalledWith(DeviceSelectionPopupComponent, {
        panelClass: 'custom-dialog-container',
        data: { selectedDevice: initialDevice },
      });
      expect(component.selectedDevice).toBe(changedDevice);
    }));

    it('should not change selectedDevice and selectedDevicePort if dialog is closed without result', fakeAsync(() => {
      const changedDevice = Device.sampleLocal(Device.sample(), 1884);
      const expectedPort = 1883;
      component.selectedDevice = Device.sampleLocal(
        Device.sample(),
        expectedPort,
      );

      const mockDialogRef = {
        afterClosed: () => of(null),
      };
      dialog.open.mockReturnValue(mockDialogRef);

      component.openDeviceSelectionDialog();

      expect(dialog.open).toHaveBeenCalled();
      expect(component.selectedDevice.port).toBe(expectedPort);
    }));
  });

  describe('onModelSelection', () => {
    it('should create model and set model_id', async () => {
      const mockFileHandle = Files.sample('model.bin');
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
      component.selectedDevice = Device.sampleLocal();
      component.selectedDevice.connection_state = DeviceStatus.Disconnected;
      const newStatus = DeviceStatus.Connected;
      const updatedDevice = Device.sampleLocal();
      updatedDevice.connection_state = newStatus;

      deviceService.getDeviceV2.mockResolvedValue(updatedDevice);

      await component.refreshDeviceStatus();

      expect(deviceService.getDeviceV2).toHaveBeenCalledWith(
        component.selectedDevice.device_id,
      );
      expect(component.selectedDevice.connection_state).toEqual(newStatus);
    });

    it('should not update the status if no device selected', async () => {
      component.selectedDevice = undefined;
      const newStatus = DeviceStatus.Connected;
      const updatedDevice = Device.sampleLocal();
      updatedDevice.connection_state = newStatus;

      deviceService.getDeviceV2.mockResolvedValue(updatedDevice);

      await component.refreshDeviceStatus();

      expect(deviceService.getDeviceV2).not.toHaveBeenCalled();
    });
  });

  describe('onDeploy', () => {
    it('should deploy successfully when all conditions are met', async () => {
      const port = 1883;
      component.selectedDevice = Device.sampleLocal(Device.sample(), port);
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
      component.selectedDevice = Device.sampleLocal(Device.sample(), 1883);
      component.app_id = 'app123';
      component.model_id = 'model123';
      component.cam_fw_file_id = 'firmwarefile123';
      component.sensor_fw_file_id = 'firmwarefile456';
      component.bodyForm.controls['camFwControl'].setValue('1.0.0');
      component.bodyForm.controls['sensorFwControl'].setValue('1.0.0');
      component.cam_fw_deploy = true;
      component.sensor_fw_deploy = true;
      dialog.afterCloseVal = false;
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
      component.selectedDevice = Device.sampleLocal(Device.sample(), port);
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
    let selectedDevicePort = 1883;

    beforeEach(() => {
      // set initial values different from default
      component.selectedDevice = Device.sampleLocal(
        Device.sample(selectedDevice),
        selectedDevicePort,
      );

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
});
