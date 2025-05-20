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
import { LOCALE_ID } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { DeviceStatus, LocalDevice } from '@app/core/device/device';
import { DeviceService } from '@app/core/device/device.service';
import { Device } from '@samplers/device';
import { Subject } from 'rxjs';
import { DeviceSelectionPopupComponent } from './device-selector-popup.component';

class MockDeviceService {
  deleteDevice = jest.fn().mockResolvedValue(undefined);
  setSelectedDevice = jest.fn();
  loadDevices = jest.fn().mockResolvedValue(undefined);
  devices$ = new Subject<LocalDevice[]>();
}

describe('DeviceSelectionPopupComponent', () => {
  let component: DeviceSelectionPopupComponent;
  let fixture: ComponentFixture<DeviceSelectionPopupComponent>;
  let deviceService: MockDeviceService;
  let dialog: jest.Mocked<DialogRef<LocalDevice>>;

  beforeEach(async () => {
    const mockDialogRef = {
      close: jest.fn(),
    } as unknown as jest.Mocked<DialogRef<LocalDevice>>;

    await TestBed.configureTestingModule({
      imports: [DeviceSelectionPopupComponent],
      providers: [
        { provide: DeviceService, useClass: MockDeviceService },
        { provide: DialogRef, useValue: mockDialogRef },
        { provide: DIALOG_DATA, useValue: {} },
        { provide: LOCALE_ID, useValue: 'en-US' },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DeviceSelectionPopupComponent);
    deviceService = TestBed.inject(
      DeviceService,
    ) as unknown as MockDeviceService;
    dialog = TestBed.inject(DialogRef) as jest.Mocked<DialogRef<LocalDevice>>;
    component = fixture.componentInstance;

    fixture.detectChanges();
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should load devices and update the component', () => {
    const partialDevices: Partial<LocalDevice>[] = [
      { device_name: 'Device 1', connection_state: DeviceStatus.Connected },
      { device_name: 'Device 2', connection_state: DeviceStatus.Disconnected },
    ];

    const testDevices = partialDevices.map((device) => Device.sample(device));

    // simulate population of devices
    deviceService.devices$.next(testDevices);
    fixture.detectChanges();

    expect(component.devices().length).toBe(2);
    expect(component.devices()[0].device_name).toBe('Device 1');
    expect(component.devices()[0].connection_state).toBe(
      DeviceStatus.Connected,
    );
    expect(component.devices()[1].device_name).toBe('Device 2');
    expect(component.devices()[1].connection_state).toBe(
      DeviceStatus.Disconnected,
    );
  });

  it('should close the dialog on cancel, but maintain previous selected device', () => {
    const devicev2 = Device.sample({
      device_name: 'Device 1',
    });

    deviceService.devices$.next([devicev2]);
    component.data.selectedDevice = devicev2;
    component.onCancel();
    expect(dialog.close).toHaveBeenCalledWith(devicev2);
  });

  it('should close the dialog with selected device on select', () => {
    const devicev2 = Device.sample({
      device_name: 'Device 1',
    });

    component.selectedDevice = devicev2;
    component.onSelect();
    expect(dialog.close).toHaveBeenCalledWith(devicev2);
  });

  it('should maintain selected device even if refresh is clicked', async () => {
    const devicev2 = Device.sample({
      device_name: 'Device 1',
    });

    // add defaults
    const testDevices: LocalDevice[] = [Device.sample(devicev2)];

    deviceService.devices$.next(testDevices);

    component.selectedDevice = devicev2;
    await component.refresh();
    expect(component.selectedDevice?.device_name).toBe(devicev2.device_name);
    expect(component.selectedDevice).toStrictEqual(devicev2);
  });

  it('should update device when onDeviceSelected', async () => {
    const devicev2 = Device.sample({
      device_name: 'Device 1',
    });

    component.onDeviceSelected(devicev2);
    expect(component.selectedDevice).toStrictEqual(devicev2);
  });
});
