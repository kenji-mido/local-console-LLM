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
import { MatDialogModule } from '@angular/material/dialog';
import { DeviceStatus } from '@app/core/device/device';
import { DeviceService } from '@app/core/device/device.service';
import { DialogService } from '@app/layout/dialogs/dialog.service';
import { ButtonVariant } from '@app/layout/dialogs/user-prompt/action';
import { DeviceList } from '@samplers/device';
import { of } from 'rxjs';
import { DeviceManagementScreen, Tab } from './device-management.screen';
import { UserPromptNameDialog } from './user-prompt-name/user-prompt-name.dialog';

class MockDeviceService {
  devices$ = of(DeviceList.sample().devices);

  loadDevices = jest.fn();
  deleteDevice = jest.fn();
  updateDeviceName = jest.fn();
  getDevice = jest.fn();
}

class MockDialogService {
  prompt = jest.fn();
  open = jest.fn();
}

describe('DeviceManagementScreen', () => {
  let component: DeviceManagementScreen;
  let fixture: ComponentFixture<DeviceManagementScreen>;
  let deviceService: MockDeviceService;
  let dialogService: MockDialogService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DeviceManagementScreen, MatDialogModule],
      providers: [
        { provide: DeviceService, useClass: MockDeviceService },
        { provide: DialogService, useClass: MockDialogService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DeviceManagementScreen);
    component = fixture.componentInstance;
    deviceService = TestBed.inject(
      DeviceService,
    ) as unknown as MockDeviceService;
    dialogService = TestBed.inject(
      DialogService,
    ) as unknown as MockDialogService;
    fixture.detectChanges();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should create the component', () => {
    expect(component).toBeTruthy();
  });

  it('should load devices on initialization using the sampler', () => {
    expect(deviceService.loadDevices).toHaveBeenCalled();
    expect(component.devices()).toEqual(DeviceList.sample().devices);
  });

  it('should display device details correctly from sampler', () => {
    const displayedColumns = component.displayedColumns;
    expect(displayedColumns).toContain('device_name');
    expect(displayedColumns).toContain('status');
    expect(displayedColumns).toContain('port');
    expect(displayedColumns).toContain('appFw');
    expect(displayedColumns).toContain('sensorFw');
  });

  it('should handle different device statuses correctly', () => {
    const devices = DeviceList.sample().devices;

    // Check device statuses from the sampler
    expect(devices[0].connection_state).toBe(DeviceStatus.Connected);
    expect(devices[1].connection_state).toBe(DeviceStatus.Disconnected);
    expect(devices[2].connection_state).toBe(DeviceStatus.Connecting);
  });

  it('should select a device and update selectedDeviceId', async () => {
    const device = DeviceList.sample().devices[0];
    deviceService.getDevice.mockReturnValue(Promise.resolve(device));
    await component.onDeviceSelected(device);

    expect(component.selectedDeviceId).toBe(device.device_id);
    expect(component.selectedDevice).toBe(device);
  });

  it('should switch between tabs', () => {
    component.selectNetwork();
    expect(component.selectedSection).toBe(Tab.Network);

    component.selectModel();
    expect(component.selectedSection).toBe(Tab.Model);

    component.selectDevice();
    expect(component.selectedSection).toBe(Tab.Device);
  });

  it('should resize device details pane on drag move', () => {
    // We select a device to make the details pane appear
    const device = DeviceList.sample().devices[0];
    deviceService.getDevice.mockReturnValue(Promise.resolve(device));
    component.onDeviceSelected(device);

    const initialInfoSize = component.initialInfoSize;
    const mockEvent = {
      distance: { y: -10 },
      source: { setFreeDragPosition: jest.fn() },
    } as any;

    component.onDragMoved(mockEvent);
    expect(component.infoSize).toBe(initialInfoSize + 10);

    component.onDragEnded({} as any);
    expect(component.initialInfoSize).toBe(component.infoSize);
  });

  it('should open the delete confirmation dialog and delete the device on confirmation', async () => {
    const device = DeviceList.sample().devices[0];

    dialogService.prompt.mockReturnValue(Promise.resolve({ id: 'delete' }));

    // select a device
    component.onDeviceSelected(device);
    expect(component.selectedDevice).toBe(device);

    await component.onDelete(device);

    expect(dialogService.prompt).toHaveBeenCalledWith({
      message: `'${device.device_name}' will be removed from Local Console.  Existing image and metadata will not be removed.`,
      title: 'Are you sure you want to delete the device?',
      actionButtons: [
        { id: 'delete', text: 'Delete', variant: ButtonVariant.negative },
      ],
      type: 'warning',
      showCancelButton: true,
    });

    expect(deviceService.deleteDevice).toHaveBeenCalled();
    // verify selected device variables are null
    expect(component.selectedDevice).toBeNull();
    expect(component.selectedDeviceId).toBeNull();

    jest.restoreAllMocks();
  });

  it('should not delete the device if dialog is canceled', async () => {
    const device = DeviceList.sample().devices[0]; // Sample device

    dialogService.prompt.mockReturnValue(Promise.resolve(null));

    await component.onDelete(device);

    expect(dialogService.prompt).toHaveBeenCalled();
    expect(deviceService.deleteDevice).not.toHaveBeenCalled();

    jest.restoreAllMocks();
  });

  it('should open the rename dialog and rename the device on confirmation', async () => {
    const device = DeviceList.sample().devices[0];

    const mockDialogRef = {
      closed: of('new-device-name'),
    };

    dialogService.open.mockReturnValue(mockDialogRef);

    await component.onRename(device);

    expect(dialogService.open).toHaveBeenCalledWith(UserPromptNameDialog, {
      title: 'Rename Device',
      message: '',
      actionButtons: [
        { id: 'rename', text: 'Rename', variant: ButtonVariant.normal },
      ],
      type: 'warning',
      showCancelButton: true,
      deviceName: device.device_name,
    });

    expect(deviceService.updateDeviceName).toHaveBeenCalledWith(
      device.device_id,
      'new-device-name',
    );
  });

  it('should not rename the device if dialog is canceled or no name is provided', async () => {
    const device = DeviceList.sample().devices[0];

    const mockDialogRef = {
      closed: of(null),
    };

    dialogService.open.mockReturnValue(mockDialogRef);

    await component.onRename(device);

    expect(dialogService.open).toHaveBeenCalled();
    expect(deviceService.updateDeviceName).not.toHaveBeenCalled();
  });

  it('should not deselect device if another device is deleted', async () => {
    const device = DeviceList.sample().devices[0];
    const device2 = DeviceList.sample().devices[1];

    dialogService.prompt.mockReturnValue(Promise.resolve({ id: 'delete' }));

    component.onDeviceSelected(device);
    await component.onDelete(device2);

    expect(deviceService.deleteDevice).toHaveBeenCalledWith(device2);
    expect(component.selectedDevice).toBe(device);
    expect(component.selectedDeviceId).toBe(device.device_id);
  });
});
