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
import { DeployConfirmPopupComponent } from './deploy-confirm-popup.component';
import { DeviceService } from '@app/core/device/device.service';
import { DeviceV2, DeviceStatus } from '@app/core/device/device';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { LOCALE_ID } from '@angular/core';
import { Subject } from 'rxjs';
import { Device } from '@samplers/device';

class MockDeviceService {
  deleteDevice = jest.fn().mockResolvedValue(undefined);
  setSelectedDevice = jest.fn();
  loadDevices = jest.fn().mockResolvedValue(undefined);
  devices$ = new Subject<DeviceV2[]>();
}

describe('DeviceSelectionPopupComponent', () => {
  let component: DeployConfirmPopupComponent;
  let fixture: ComponentFixture<DeployConfirmPopupComponent>;
  let deviceService: MockDeviceService;
  let dialog: jest.Mocked<MatDialogRef<DeployConfirmPopupComponent>>;

  beforeEach(async () => {
    const mockDialogRef = {
      close: jest.fn(),
    } as unknown as jest.Mocked<MatDialogRef<DeployConfirmPopupComponent>>;

    await TestBed.configureTestingModule({
      imports: [DeployConfirmPopupComponent],
      providers: [
        { provide: MatDialogRef, useValue: mockDialogRef },
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            mainChipFw: 'mock',
            sensorChipFw: 'mock',
            selectedDeviceName: Device.sample().device_name,
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DeployConfirmPopupComponent);
    dialog = TestBed.inject(MatDialogRef) as jest.Mocked<
      MatDialogRef<DeployConfirmPopupComponent>
    >;
    component = fixture.componentInstance;

    fixture.detectChanges();
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
    expect(component.mainChipFw).toBe('mock');
    expect(component.sensorChipFw).toBe('mock');
    expect(component.selectedDeviceName).toBe('device_xyz');
  });

  it('should close the dialog on cancel', () => {
    component.onCancel();
    expect(dialog.close).toHaveBeenCalledWith(false);
  });

  it('should close the dialog on deploy', () => {
    component.onDeploy();
    expect(dialog.close).toHaveBeenCalledWith(true);
  });
});
