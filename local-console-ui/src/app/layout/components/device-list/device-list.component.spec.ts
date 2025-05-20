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
import { LocalDevice } from '@app/core/device/device';
import { DeviceService } from '@app/core/device/device.service';
import { DialogService } from '@app/layout/dialogs/dialog.service';
import { DeviceList } from '@samplers/device';
import { Subject } from 'rxjs';
import { DeviceListComponent } from './device-list.component';

class MockDeviceService {
  deleteDevice = jest.fn().mockReturnValue(Promise.resolve());
  setSelectedDevice = jest.fn();
  loadDevices = jest.fn().mockImplementation(() => Promise.resolve());
  devices$ = new Subject<LocalDevice[]>();
}

class MockDialogService {
  prompt = jest.fn().mockReturnValue(Promise.resolve()); // Simulates dismisal
}

describe('DeviceListComponent', () => {
  let component: DeviceListComponent;
  let fixture: ComponentFixture<DeviceListComponent>;
  let deviceService: MockDeviceService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DeviceListComponent],
      providers: [
        { provide: DeviceService, useClass: MockDeviceService },
        { provide: DialogService, useClass: MockDialogService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DeviceListComponent);
    deviceService = TestBed.inject(
      DeviceService,
    ) as unknown as MockDeviceService;
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('devices$ subscription', () => {
    it('should update devices and refresh date time on successful device fetch', async () => {
      const deviceList = DeviceList.sample();
      deviceService.devices$.next(deviceList.devices);
      fixture.detectChanges();
      expect(component.devices).toEqual(deviceList.devices);
    });
  });
});
