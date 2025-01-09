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

import { AIModelInfo } from './aimodel-info.component';
import { DeviceV2 } from '@app/core/device/device';
import { EdgeAppModuleStateV2 } from '@app/core/module/edgeapp';
import { SysAppModuleStateV2, isSysModuleState } from '@app/core/module/sysapp';
import { Device } from '@samplers/device';
import { ComponentFixture, TestBed } from '@angular/core/testing';

describe('DeviceInfoComponent', () => {
  let component: AIModelInfo;
  let fixture: ComponentFixture<AIModelInfo>;
  const device_info_null = [
    {
      model_id: undefined,
      version: undefined,
      conv_version: undefined,
    },
  ];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AIModelInfo],
    }).compileComponents();

    fixture = TestBed.createComponent(AIModelInfo);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  describe('onDeviceInfoReceived', () => {
    it('should define all elements undefined if device is null', () => {
      const device: DeviceV2 | null = null;
      component.onDeviceInfoReceived(device);
      expect(component.aimodels_info).toEqual(device_info_null);
    });
    it('should define all elements undefined if modules is null', () => {
      let device: DeviceV2 | null = Device.sample();
      device.modules = undefined;
      component.onDeviceInfoReceived(device);
      expect(component.aimodels_info).toEqual(device_info_null);
    });
    it('should define all elements undefined if ai_models is null', () => {
      let device: DeviceV2 | null = Device.sample();
      if (
        device.modules?.[0].property.state &&
        isSysModuleState(device.modules?.[0].property.state!)
      ) {
        device.modules[0].property.state.device_info!.ai_models = undefined;
      }
      component.onDeviceInfoReceived(device);
      expect(component.aimodels_info).toEqual(device_info_null);
    });
    it('should define all elements undefined if not sysmodules', () => {
      let device: DeviceV2 | null = Device.sample();
      const edge_app_state: EdgeAppModuleStateV2 = { edge_app: undefined };
      if (device.modules?.[0].property.state) {
        device.modules[0].property.state = edge_app_state;
      }
      component.onDeviceInfoReceived(device);
      expect(component.aimodels_info).toEqual(device_info_null);
    });
    it('should define all elements correctly', () => {
      let device: DeviceV2 | null = Device.sample();
      component.onDeviceInfoReceived(device);
      if (isSysModuleState(device.modules?.[0].property.state!)) {
        let device_state: SysAppModuleStateV2 =
          device.modules?.[0].property.state!;
        expect(component.num_models[-1] === 2);
        for (let i = 0; i < component.num_models[-1]; i++) {
          expect(component.aimodels_info[i].model_id).toEqual(
            device_state.device_info?.ai_models?.[i].name,
          );
          expect(component.aimodels_info[i].conv_version).toEqual(
            device_state.device_info?.ai_models?.[i].converter_version,
          );
          expect(component.aimodels_info[i].version).toEqual(
            device_state.device_info?.ai_models?.[i].version,
          );
        }
      }
    });
  });
});
