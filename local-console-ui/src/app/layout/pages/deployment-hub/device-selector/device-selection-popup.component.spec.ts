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
import { DeviceSelectionPopupComponent } from './device-selection-popup.component';
import { DeviceService } from '@app/core/device/device.service';
import { DeviceV2, DeviceStatus } from '@app/core/device/device';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { LOCALE_ID } from '@angular/core';
import { Subject, of } from 'rxjs';
import { toSignal } from '@angular/core/rxjs-interop';

class MockDeviceService {
  deleteDevice = jest.fn().mockResolvedValue(undefined);
  setSelectedDevice = jest.fn();
  loadDevices = jest.fn().mockResolvedValue(undefined);
  devices$ = new Subject<DeviceV2[]>();
}

describe('DeviceSelectionPopupComponent', () => {
  let component: DeviceSelectionPopupComponent;
  let fixture: ComponentFixture<DeviceSelectionPopupComponent>;
  let deviceService: MockDeviceService;
  let dialog: jest.Mocked<MatDialogRef<DeviceSelectionPopupComponent>>;

  beforeEach(async () => {
    const mockDialogRef = {
      close: jest.fn(),
    } as unknown as jest.Mocked<MatDialogRef<DeviceSelectionPopupComponent>>;

    await TestBed.configureTestingModule({
      imports: [DeviceSelectionPopupComponent],
      providers: [
        { provide: DeviceService, useClass: MockDeviceService },
        { provide: MatDialogRef, useValue: mockDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: {} },
        { provide: LOCALE_ID, useValue: 'en-US' },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DeviceSelectionPopupComponent);
    deviceService = TestBed.inject(
      DeviceService,
    ) as unknown as MockDeviceService;
    dialog = TestBed.inject(MatDialogRef) as jest.Mocked<
      MatDialogRef<DeviceSelectionPopupComponent>
    >;
    component = fixture.componentInstance;

    fixture.detectChanges();
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should load devices and update the component', () => {
    const partialDevices: Partial<DeviceV2>[] = [
      { device_name: 'Device 1', connection_state: DeviceStatus.Connected },
      { device_name: 'Device 2', connection_state: DeviceStatus.Disconnected },
    ];

    // add defaults
    const testDevices: DeviceV2[] = partialDevices.map((device) => ({
      device_id: '',
      description: '',
      internal_device_id: '',
      inactivity_timeout: 0,
      device_groups: [],
      device_name: '',
      connection_state: DeviceStatus.Unknown,
      ...device,
    }));

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
    const devicev2: DeviceV2 = {
      device_name: 'Device 1',
      connection_state: DeviceStatus.Connected,
      device_id: '',
      description: '',
      internal_device_id: '',
      inactivity_timeout: 0,
      device_groups: [],
    };
    const partialDevices: Partial<DeviceV2>[] = [devicev2];

    // add defaults
    const testDevices: DeviceV2[] = partialDevices.map((device) => ({
      device_id: '',
      description: '',
      internal_device_id: '',
      inactivity_timeout: 0,
      device_groups: [],
      device_name: '',
      connection_state: DeviceStatus.Unknown,
      ...device,
    }));

    deviceService.devices$.next(testDevices);
    component.selectedDevice = devicev2.device_name;
    component.onCancel();
    expect(dialog.close).toHaveBeenCalledWith(devicev2);
  });

  it('should close the dialog with selected device on select', () => {
    const devicev2: DeviceV2 = {
      device_name: 'Device 1',
      connection_state: DeviceStatus.Connected,
      device_id: '',
      description: '',
      internal_device_id: '',
      inactivity_timeout: 0,
      device_groups: [],
    };

    const device_v2: DeviceV2 = devicev2;
    component.device = device_v2;
    component.onSelect();
    expect(dialog.close).toHaveBeenCalledWith(device_v2);
  });
});
