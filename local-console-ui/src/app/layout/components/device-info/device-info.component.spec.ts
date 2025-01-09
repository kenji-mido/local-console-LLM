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

import { DeviceInfo } from './device-info.component';
import { DeviceV2 } from '@app/core/device/device';
import { EdgeAppModuleStateV2 } from '@app/core/module/edgeapp';
import { SysAppModuleStateV2, isSysModuleState } from '@app/core/module/sysapp';
import { Device } from '@samplers/device';
import { ComponentFixture, TestBed } from '@angular/core/testing';

describe('DeviceInfoComponent', () => {
  let component: DeviceInfo;
  let fixture: ComponentFixture<DeviceInfo>;
  const device_info_null = {
    sensor: undefined,
    main_chip: undefined,
    sensor_chip_fw_main: undefined,
    sensor_chip_fw_loader: undefined,
    processing_state: undefined,
    device_id: undefined,
    internal_id: undefined,
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DeviceInfo],
    }).compileComponents();

    fixture = TestBed.createComponent(DeviceInfo);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  describe('onDeviceInfoReceived', () => {
    it('should define all elements undefined if device is null', () => {
      const device: DeviceV2 | null = null;
      component.onDeviceInfoReceived(device);
      expect(component.device_info).toEqual(device_info_null);
    });
    it('should define all elements undefined if modules is null', () => {
      let device: DeviceV2 | null = Device.sample();
      device.modules = undefined;
      component.onDeviceInfoReceived(device);
      expect(component.device_info).toEqual(device_info_null);
    });
    it('should define all elements undefined if not sysmodules', () => {
      let device: DeviceV2 | null = Device.sample();
      const edge_app_state: EdgeAppModuleStateV2 = { edge_app: undefined };
      if (device.modules?.[0].property.state) {
        device.modules[0].property.state = edge_app_state;
      }
      component.onDeviceInfoReceived(device);
      expect(component.device_info).toEqual(device_info_null);
    });
    it('should define all elements correctly', () => {
      let device: DeviceV2 | null = Device.sample();
      component.onDeviceInfoReceived(device);
      if (isSysModuleState(device.modules?.[0].property.state!)) {
        let device_state: SysAppModuleStateV2 =
          device.modules?.[0].property.state!;

        expect(component.device_info.device_id).toEqual(device.device_id);
        expect(component.device_info.internal_id).toEqual(
          device.internal_device_id,
        );
        expect(component.device_info.main_chip).toEqual(
          device_state.device_info?.processors?.[0].firmware_version,
        );
        expect(component.device_info.processing_state).toEqual(
          device_state.device_state?.process_state,
        );
        expect(component.device_info.sensor).toEqual(
          device_state.device_info?.sensors?.[0].name,
        );
        expect(component.device_info.sensor_chip_fw_loader).toEqual(
          device_state.device_info?.sensors?.[0].loader_version,
        );
        expect(component.device_info.sensor_chip_fw_main).toEqual(
          device_state.device_info?.sensors?.[0].firmware_version,
        );
      }
    });
  });
});
