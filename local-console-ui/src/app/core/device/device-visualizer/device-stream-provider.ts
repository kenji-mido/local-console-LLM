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

import { Point2D } from '@app/core/drawing/drawing';
import { ExtendedMode, Mode } from '@app/core/inference/inference';
import { Observable } from 'rxjs';
import { OperationMode } from '../configuration';
import { DeviceFrame } from '../device';

export interface DeviceStream {
  stream: Observable<DeviceFrame>;
  detach: Promise<void>;
}

export interface DeviceStreamProvider {
  init(
    device_id: string,
    roiOffset: Point2D,
    roiSize: Point2D,
    mode: Mode | ExtendedMode,
  ): Promise<void>;
  teardown(device_id: string): Promise<void>;
  getNextFrame(
    device_id: string,
    mode: Mode | ExtendedMode,
    expectedType: OperationMode,
    abortSignal: AbortSignal,
    lastFrame: DeviceFrame | undefined,
  ): Promise<DeviceFrame | Error>;
}
