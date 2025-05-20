/**
 * Copyright 2025 Sony Semiconductor Solutions Corp.
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

import { Injectable } from '@angular/core';
import { ExecuteCommandPayloadV2 } from '@app/core/command/command';
import { CommandService } from '@app/core/command/command.service';
import { Point2D } from '@app/core/drawing/drawing';
import { ExtendedMode, Mode } from '@app/core/inference/inference';
import { DTDLResInfoV2 } from '@app/core/module/dtdl';
import { DeviceFrame } from '../device';
import { DeviceStreamProvider } from '../device-visualizer/device-stream-provider';
import { DeviceService } from '../device.service';

export enum FlipOption {
  normal = 0,
  flip = 1,
}

export interface DirectGetImageParameters {
  crop_h_offset: number;
  crop_v_offset: number;
  crop_h_size: number;
  crop_v_size: number;
  network_id: '999999'; // High-res model
}

export interface DirectGetImageCommand
  extends ExecuteCommandPayloadV2<DirectGetImageParameters> {
  extra: {
    preview?: boolean;
    stop?: boolean;
  };
}

export interface DirectGetImageResponse {
  res_info: DTDLResInfoV2;
  image: string;
}

@Injectable({
  providedIn: 'root',
})
export class DirectImageStreamService implements DeviceStreamProvider {
  constructor(
    private devices: DeviceService,
    private commands: CommandService,
  ) {}

  async init(
    device_id: string,
    roiOffset: Point2D,
    roiSize: Point2D,
    mode: Mode | ExtendedMode,
  ) {
    this.devices.setLastKnownRoiCache(device_id, {
      offset: roiOffset,
      size: roiSize,
    });
  }

  async teardown(device_id: string) {
    // Issue a shell command...
    const payload: DirectGetImageCommand = {
      command_name: 'direct_get_image',
      parameters: {
        crop_h_offset: 0,
        crop_v_offset: 0,
        crop_h_size: 0,
        crop_v_size: 0,
        network_id: '999999',
      },
      extra: {
        stop: true, //... that requests the image pulling loop to stop
      },
    };
    await this.commands.executeSysAppCommand(device_id, payload);
  }

  async getNextFrame(
    device_id: string,
    mode: Mode | ExtendedMode,
  ): Promise<DeviceFrame | Error> {
    const roi = this.devices.getLastKnownRoiCache(device_id);
    const payload: DirectGetImageCommand = {
      command_name: 'direct_get_image',
      parameters: {
        crop_h_offset: roi.offset.x,
        crop_v_offset: roi.offset.y,
        crop_h_size: roi.size.x,
        crop_v_size: roi.size.y,
        network_id: '999999',
      },
      extra: {
        preview: mode === ExtendedMode.Preview,
      },
    };
    try {
      const result = await this.commands.executeSysAppCommand(
        device_id,
        payload,
      );
      if (!result.command_response || result.result !== 'SUCCESS') {
        return new Error(
          'Failed to obtain image from device: RPC returned failure',
        );
      }
      return this.toFrame(
        result.command_response as unknown as DirectGetImageResponse,
      );
    } catch (cause) {
      const err = new Error(
        'Failed to obtain image from device: Unknown error',
        { cause },
      );
      console.error(err);
      return err;
    }
  }

  private toFrame(response: DirectGetImageResponse): DeviceFrame | Error {
    if (!response.image || response.res_info.code) {
      return new Error(
        `Failed to obtain image from device: No image found ('${response.res_info.code}')`,
      );
    }
    return <DeviceFrame>{
      identifier: Date.now().toString(),
      image: 'data:image/jpeg;base64,' + response.image,
    };
  }
}
