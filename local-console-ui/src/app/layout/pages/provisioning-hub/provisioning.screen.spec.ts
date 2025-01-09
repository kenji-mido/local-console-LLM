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
import { FeaturesService } from '@app/core/common/features.service';
import { DeviceService } from '@app/core/device/device.service';
import { DeviceV2, LocalDevice } from '@app/core/device/device';
import { ReplaySubject } from 'rxjs';
import { Component, Input } from '@angular/core';
import { ProvisioningScreen } from './provisioning.screen';
import { NetworkSettingsPane } from './network-settings/network-settings.pane';
import { DeviceDetailsComponent } from '@app/core/device/device-details/device-details.component';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { FormControl } from '@angular/forms';
import { Device, DeviceList } from '@samplers/device';

class MockDeviceService {
  deleteDevice = jest.fn().mockReturnValue(Promise.resolve());
  setSelectedDevice = jest.fn();
  loadDevices = jest.fn().mockImplementation(() => Promise.resolve());
  devices$ = new ReplaySubject<DeviceV2[]>(1);
  createDevice = jest.fn().mockResolvedValue(null);
}

class MockFeaturesService {
  getFeatures = jest.fn().mockReturnValue({
    device_list: {
      full: true,
      local_devices: true,
    },
    device_registration: {
      mqtt_port: true,
    },
  });
}

@Component({
  selector: 'app-network-settings',
  template: '<div></div>',
  standalone: true,
})
export class MockNetworkSettingsPane {
  @Input()
  mqttPort?: number;
}

@Component({
  selector: 'app-device-details',
  template: '<div></div>',
  standalone: true,
})
export class MockStreamingPreviewComponent {
  @Input()
  selectedDevice?: LocalDevice;
}

describe('DeviceListComponent', () => {
  let component: ProvisioningScreen;
  let fixture: ComponentFixture<ProvisioningScreen>;
  let deviceService: MockDeviceService;
  let featuresService: MockFeaturesService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        ProvisioningScreen,
        NoopAnimationsModule,
        MockNetworkSettingsPane,
      ],
      providers: [
        { provide: DeviceService, useClass: MockDeviceService },
        { provide: FeaturesService, useClass: MockFeaturesService },
      ],
    })
      .overrideComponent(ProvisioningScreen, {
        remove: { imports: [NetworkSettingsPane, DeviceDetailsComponent] },
        add: {
          imports: [MockNetworkSettingsPane, MockStreamingPreviewComponent],
        },
      })
      .compileComponents();

    fixture = TestBed.createComponent(ProvisioningScreen);
    deviceService = TestBed.inject(
      DeviceService,
    ) as unknown as MockDeviceService;
    featuresService = TestBed.inject(
      FeaturesService,
    ) as unknown as MockFeaturesService;
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('refresh', () => {
    it('should set isLoading to true and then to false', async () => {
      expect(component.isLoading).toBe(false);
      const refreshPromise = component.refresh();
      expect(component.isLoading).toBe(true);
      await refreshPromise;
      expect(component.isLoading).toBe(false);
    });

    it('should call loadDevices', async () => {
      await component.refresh();
      expect(deviceService.loadDevices).toHaveBeenCalled();
    });
  });

  describe('createDevice', () => {
    it('should call the service with the correct parameters', async () => {
      const device_name = 'My device';
      const mqtt_port = 12345;
      const device = Device.sampleLocal(Device.sample(device_name), mqtt_port);
      const devices = DeviceList.sampleLocal().devices;
      devices.push(device);

      deviceService.devices$.next(devices);
      component.createDeviceGroup.setControl(
        'device_name',
        new FormControl(device_name, { nonNullable: true }),
      );
      component.createDeviceGroup.setControl(
        'mqtt_port',
        new FormControl(mqtt_port.toString(), { nonNullable: true }),
      );

      // HACK: deviceService.createDevice returns null when it raises an exception
      deviceService.createDevice.mockReturnValue({});
      await component.createDevice();

      expect(deviceService.createDevice).toHaveBeenCalledWith(
        device_name,
        mqtt_port,
      );
      expect(component.selectedDevice).toBe(device);
    });
  });
});
