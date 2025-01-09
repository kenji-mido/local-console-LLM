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

import { NgModule, Pipe, PipeTransform } from '@angular/core';
import { DeviceV2 } from '../device/device';
import { isSysModule } from '../module/module';

@Pipe({
  name: 'processorFwVersion',
  standalone: true,
})
export class ProcessorFirmwarePipe implements PipeTransform {
  transform(device: DeviceV2): string | undefined {
    const sysModule = device.modules?.find(isSysModule);
    const firstValidProcessor =
      sysModule?.property.state?.device_info?.processors?.find(
        (p) => !!p.firmware_version,
      );
    return firstValidProcessor?.firmware_version;
  }
}

@Pipe({
  name: 'sensorFwVersion',
  standalone: true,
})
export class SensorFirmwarePipe implements PipeTransform {
  transform(device: DeviceV2): string | undefined {
    const sysModule = device.modules?.find(isSysModule);
    const imx500Sensor = sysModule?.property.state?.device_info?.sensors?.find(
      (s) => s.name === 'IMX500',
    );
    return imx500Sensor?.firmware_version;
  }
}

@NgModule({
  imports: [ProcessorFirmwarePipe, SensorFirmwarePipe],
  exports: [ProcessorFirmwarePipe, SensorFirmwarePipe],
})
export class FirmwarePipesModule {}
