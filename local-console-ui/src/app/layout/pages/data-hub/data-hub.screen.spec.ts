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

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DataHubScreen, LabelsStored } from './data-hub.screen';
import { DeviceService } from '@app/core/device/device.service';
import { of, ReplaySubject, Subject } from 'rxjs';
import {
  DeviceFrame,
  LocalDevice,
  UpdateModuleConfigurationPayloadV2,
} from '@app/core/device/device';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { DialogService } from '@app/layout/dialogs/dialog.service';
import { MatDialog } from '@angular/material/dialog';
import { DeviceList, Device } from '@samplers/device';
import { Files } from '@samplers/file';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import {
  DrawingSurfaceComponent,
  SurfaceMode,
} from '@app/core/drawing/drawing-surface.component';
import { DeviceVisualizerComponent } from '@app/core/device/device-visualizer/device-visualizer.component';
import { ClassificationType } from 'typescript';
import { ToastComponent } from '@app/layout/components/toast/toast';
import { MatSnackBar } from '@angular/material/snack-bar';

class MockDeviceService {
  devices$ = of(DeviceList.sample().devices);

  loadDevices = jest.fn();
  deleteDevice = jest.fn();
  updateDeviceName = jest.fn();
  getDeviceV2 = jest.fn();
  patchConfiguration = jest.fn();
  getConfiguration = jest.fn();
  updateModuleConfigurationV2 = jest.fn();
  startUploadInferenceData = jest.fn();
  stopUploadInferenceData = jest.fn();
  getDeviceStream = jest.fn();
}

class MockDialogService {
  prompt = jest.fn();
  open = jest.fn();
  alert = jest.fn();
}

class MockMatDialog {
  deviceSelectionReturn = new ReplaySubject<LocalDevice>(1);
  open = jest
    .fn()
    .mockReturnValue({ afterClosed: () => this.deviceSelectionReturn });
}

class MockSnackBar {
  openFromComponent = jest.fn();
}

@Component({
  selector: 'app-device-visualizer',
  standalone: true,
  template: `<div></div>`,
})
export class MockVisualizerComponent {
  @Input() surfaceMode: SurfaceMode = 'render';
  @Input() mode: 'image-only' | 'inferred' = 'image-only';
  @Input() device?: LocalDevice;
  @Output() frameReceived = new EventEmitter<DeviceFrame>();
  @Input() labels: LabelsStored = { labels: [], applied: false };
}

describe('DataHubComponent', () => {
  let component: DataHubScreen;
  let fixture: ComponentFixture<DataHubScreen>;
  let deviceService: MockDeviceService;
  let dialogService: MockDialogService;
  let devices: MockMatDialog;
  let snackBar: MockSnackBar;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DataHubScreen, NoopAnimationsModule],
      providers: [
        { provide: MatDialog, useClass: MockMatDialog },
        { provide: DeviceService, useClass: MockDeviceService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: MatSnackBar, useClass: MockSnackBar },
      ],
    })
      .overrideComponent(DataHubScreen, {
        remove: { imports: [DeviceVisualizerComponent] },
        add: {
          imports: [MockVisualizerComponent],
        },
      })
      .compileComponents();

    fixture = TestBed.createComponent(DataHubScreen);
    deviceService = TestBed.inject(
      DeviceService,
    ) as unknown as MockDeviceService;
    dialogService = TestBed.inject(
      DialogService,
    ) as unknown as MockDialogService;
    devices = TestBed.inject(MatDialog) as unknown as MockMatDialog;
    snackBar = TestBed.inject(MatSnackBar) as unknown as MockSnackBar;
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should update parameters', async () => {
    const fileContent = '{}';
    const file = Files.sample('params.json', fileContent, 'application/json');

    await fixture.whenStable();
    await component.onPPLFileSelected(file);

    expect(deviceService.updateModuleConfigurationV2).not.toHaveBeenCalled();
    expect(component.pplParameters).toEqual(JSON.parse(fileContent));
  });

  it('should not update parameters if file is not json', async () => {
    const fileContent = '{not a valid json]';
    const file = Files.sample('params.txt', fileContent, 'application/json');

    await fixture.whenStable();
    await component.onPPLFileSelected(file);

    expect(dialogService.alert).toHaveBeenCalledWith(
      'PPL Parameters are incorrect',
      `PPL Parameters file must be a valid JSON file, with one entry per parameter`,
    );

    expect(deviceService.updateModuleConfigurationV2).not.toHaveBeenCalled();
    expect(component.pplParameters).toBe(null);
  });

  it('should update labels', async () => {
    const fileContent = 'class_1\nclass2';
    const file = Files.sample('labels.txt', fileContent);

    await fixture.whenStable();

    await component.onLabelsSelected(file);
    expect(component.labels.labels).toEqual(fileContent.split('\n'));
  });

  it('should not update labels if content is not valid', async () => {
    const fileContent = 'not valid!!!!!';
    const file = Files.sample('labels_not_valid.txt', fileContent);

    await fixture.whenStable();
    await component.onLabelsSelected(file);

    expect(dialogService.alert).toHaveBeenCalledWith(
      'Labels are incorrect',
      `Labels can only contain letters, numbers and underscores.
         There must be no blank lines between labels`,
    );

    expect(component.labels.labels).toStrictEqual([]);
  });

  it('should update labels if user is ok with too long', async () => {
    const fileContent = 'verylonglabeltotriggerwarn';
    const file = Files.sample('labels_too_long.txt', fileContent);

    await fixture.whenStable();
    const result = { id: 'ok' };
    dialogService.prompt.mockResolvedValue(result);
    await component.onLabelsSelected(file);

    expect(dialogService.prompt).toHaveBeenCalledWith({
      message: `Some of the loaded labels have more than 20 characters, which may impact readability.
            Are you sure you want to use these labels? `,
      title: 'Labels are too long',
      actionButtons: [{ id: 'ok', text: 'OK', variant: 'secondary' }],
      type: 'warning',
    });

    expect(component.labels.labels).toStrictEqual([fileContent]);
  });

  it('should not update labels if user cancels if too long', async () => {
    const fileContent = 'verylonglabeltotriggerwarn';
    const file_tl = Files.sample('labels_too_long_2.txt', fileContent);

    await fixture.whenStable();
    const result = undefined;
    dialogService.prompt.mockResolvedValue(result);
    await component.onLabelsSelected(file_tl);

    expect(dialogService.prompt).toHaveBeenCalledWith({
      message: `Some of the loaded labels have more than 20 characters, which may impact readability.
            Are you sure you want to use these labels? `,
      title: 'Labels are too long',
      actionButtons: [{ id: 'ok', text: 'OK', variant: 'secondary' }],
      type: 'warning',
    });

    expect(component.labels.labels).toStrictEqual([]);
  });

  it('should disable apply button if no device is selected', () => {
    const applyButton = fixture.debugElement.nativeElement.querySelector(
      '[data-testid="apply-configuration"]',
    );

    expect(applyButton.disabled).toBeTruthy();

    component.selectedDevice = {
      device_name: 'Device 1',
      device_id: '123',
    } as LocalDevice;
    fixture.detectChanges();

    expect(applyButton.disabled).not.toBeTruthy();
  });

  it('should call updateModuleConfigurationV2 when apply is clicked', async () => {
    const device = {
      device_name: 'Device 1',
      device_id: '123',
    } as LocalDevice;

    const pplParameters = '{"param1": "value1"}';
    component.selectedDevice = device;
    component.pplParameters = pplParameters;
    fixture.detectChanges();

    const applyButton = fixture.debugElement.nativeElement.querySelector(
      '[data-testid="apply-configuration"]',
    );
    expect(applyButton.disabled).not.toBeTruthy();
    await component.onApply();

    expect(deviceService.updateModuleConfigurationV2).toHaveBeenCalled();
    expect(snackBar.openFromComponent).toHaveBeenCalledWith(ToastComponent, {
      data: {
        message: 'Configuration Applied',
        panelClass: 'success-snackbar',
      },
      duration: 3000,
    });
  });

  it('should not call configure when mode changes', async () => {
    const device = {
      device_name: 'Device 1',
      device_id: '123',
    } as LocalDevice;

    component.selectedDevice = device;
    fixture.detectChanges();

    component.selectedDeviceConfiguration.vapp_type = 'detection';
    fixture.detectChanges();

    expect(deviceService.patchConfiguration).not.toHaveBeenCalled();
  });

  it('should update image directory path when onImagePathSelected is called', () => {
    const folderPath = '/path/to/images';
    component.onImagePathSelected(folderPath);
    expect(component.selectedDeviceConfiguration.image_dir_path).toBe(
      folderPath,
    );
  });

  it('should update inference directory path when onInferencePathSelected is called', () => {
    const folderPath = '/path/to/inference';
    component.onInferencePathSelected(folderPath);
    expect(component.selectedDeviceConfiguration.inference_dir_path).toBe(
      folderPath,
    );
  });

  //extend tests onApply
  it('should apply changes and labels', async () => {
    const MODULE_ID = 'node';
    const pplParams = '{}';
    const payload = <UpdateModuleConfigurationPayloadV2>{
      property: {
        configuration: {
          PPL_Parameters: pplParams,
        },
      },
    };
    await fixture.whenStable();

    component.selectedDevice = Device.sampleLocal();
    component.pplParameters = pplParams;
    fixture.detectChanges();
    component.operationMode = 'classification';
    fixture.detectChanges();

    component.onApply();

    expect(
      await deviceService.updateModuleConfigurationV2,
    ).toHaveBeenCalledWith(
      component.selectedDevice?.device_id,
      MODULE_ID,
      payload,
    );

    expect(await deviceService.patchConfiguration).toHaveBeenCalledWith(
      component.selectedDevice?.device_id,
      {
        vapp_type: 'classification',
        size: 100,
        inference_dir_path: null,
        image_dir_path: null,
      },
    );
  });
});
