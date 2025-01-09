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
import { DeviceListComponent } from './device-list.component';
import { FeaturesService } from '@app/core/common/features.service';
import { Device, DeviceList, DeviceModule } from '@samplers/device';
import { DeviceService } from '@app/core/device/device.service';
import { DialogService } from '@app/layout/dialogs/dialog.service';
import { DeviceV2 } from '@app/core/device/device';
import { firstValueFrom, Subject } from 'rxjs';

class MockDeviceService {
  deleteDevice = jest.fn().mockReturnValue(Promise.resolve());
  setSelectedDevice = jest.fn();
  loadDevices = jest.fn().mockImplementation(() => Promise.resolve());
  devices$ = new Subject<DeviceV2[]>();
}

class MockDialogService {
  prompt = jest.fn().mockReturnValue(Promise.resolve()); // Simulates dismisal
}

class MockFeaturesService {
  getFeatures = jest.fn().mockReturnValue({
    device_list: {
      full: true,
      local_devices: true,
    },
  });
}

describe('DeviceListComponent', () => {
  let component: DeviceListComponent;
  let fixture: ComponentFixture<DeviceListComponent>;
  let deviceService: MockDeviceService;
  let featuresService: MockFeaturesService;
  let dialogService: MockDialogService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DeviceListComponent],
      providers: [
        { provide: DeviceService, useClass: MockDeviceService },
        { provide: FeaturesService, useClass: MockFeaturesService },
        { provide: DialogService, useClass: MockDialogService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DeviceListComponent);
    deviceService = TestBed.inject(
      DeviceService,
    ) as unknown as MockDeviceService;
    featuresService = TestBed.inject(
      FeaturesService,
    ) as unknown as MockFeaturesService;
    dialogService = TestBed.inject(
      DialogService,
    ) as unknown as MockDialogService;
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

  describe('showDevice', () => {
    it('should return true if device is version 2', () => {
      const device = Device.sample();
      device.modules = [DeviceModule.sampleSystem()];
      featuresService.getFeatures.mockReturnValue({
        device_list: { local_devices: false },
      });
      fixture.detectChanges();
      expect(component.showDevice(device)).toBeTruthy();
      expect(component.features.device_list.local_devices).toBeFalsy();
    });

    it('should return true if devices are assumed to be local', () => {
      const device = Device.sample();
      expect(component.showDevice(device)).toBeTruthy();
    });

    it('should return false if device is not version 2', () => {
      const device = Device.sample();
      device.modules = [];
      featuresService.getFeatures.mockReturnValue({
        device_list: { local_devices: false },
      });
      fixture.detectChanges();
      expect(component.showDevice(device)).toBeFalsy();
    });
  });

  describe('deleteDevice', () => {
    it('should delete a local device if local_devices feature is enabled', async () => {
      const device = Device.sampleLocal();
      // Simulate someone clicking on the Delete button in confirmation dialog
      dialogService.prompt.mockReturnValue(Promise.resolve({ id: 'delete' }));

      await component.deleteDevice(device);
      expect(deviceService.deleteDevice).toHaveBeenCalledWith(device);
      expect(component.isLoading).toBe(false);
    });

    it('should not delete a device if it is not a local device', async () => {
      const device = Device.sample();
      deviceService.loadDevices.mockClear();

      await component.deleteDevice(device);

      expect(deviceService.deleteDevice).not.toHaveBeenCalled();
      expect(deviceService.loadDevices).not.toHaveBeenCalled();
      expect(component.isLoading).toBe(false);
    });

    it('should not delete a device if local_devices feature is disabled', async () => {
      const device = Device.sampleLocal();
      featuresService.getFeatures.mockReturnValue({
        device_list: { local_devices: false },
      });
      fixture.detectChanges();
      deviceService.loadDevices.mockClear();

      await component.deleteDevice(device);

      expect(deviceService.deleteDevice).not.toHaveBeenCalled();
      expect(deviceService.loadDevices).not.toHaveBeenCalled();
      expect(component.isLoading).toBe(false);
    });
  });
});
