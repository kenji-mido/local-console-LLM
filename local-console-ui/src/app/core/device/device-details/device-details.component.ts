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

import { CommonModule } from '@angular/common';
import { Component, Input, OnDestroy, viewChild } from '@angular/core';
import { ExtendedMode } from '@app/core/inference/inference';
import { DeviceStatus, LocalDevice } from '../device';
import { DeviceStatusBadgeComponent } from '../device-status/device-status-badge.component';
import { DeviceStreamingService } from '../device-visualizer/device-streaming.service';
import { DeviceVisualizerComponent } from '../device-visualizer/device-visualizer.component';
import { DevicePipesModule } from '../device.pipes';

@Component({
  selector: 'app-device-details',
  standalone: true,
  imports: [
    CommonModule,
    DevicePipesModule,
    DeviceVisualizerComponent,
    DeviceStatusBadgeComponent,
  ],
  templateUrl: './device-details.component.html',
  styleUrl: './device-details.component.scss',
})
export class DeviceDetailsComponent implements OnDestroy {
  visualizer = viewChild(DeviceVisualizerComponent);
  private __device?: LocalDevice;
  get selectedDevice() {
    return this.__device;
  }
  @Input()
  set selectedDevice(device: LocalDevice | undefined) {
    if (device?.device_id !== this.__device?.device_id) {
      this.stopStreamIfPreviewing();
    }
    this.__device = device;
  }
  DeviceStatus = DeviceStatus;
  ExtendedMode = ExtendedMode;

  constructor(private streams: DeviceStreamingService) {}

  deviceIsBusy() {
    const deviceId = this.selectedDevice?.device_id;
    if (!deviceId) return false;
    return (
      this.streams.isDeviceStreaming(deviceId) &&
      this.streams.getStreamingMode(deviceId) !== ExtendedMode.Preview
    );
  }

  ngOnDestroy(): void {
    this.stopStreamIfPreviewing();
  }

  stopStreamIfPreviewing() {
    const deviceId = this.selectedDevice?.device_id;
    if (!deviceId) return;
    if (
      this.streams.isDeviceStreaming(deviceId) &&
      this.streams.getStreamingMode(deviceId) === ExtendedMode.Preview
    )
      this.visualizer()?.stopInferenceStream();
  }
}
