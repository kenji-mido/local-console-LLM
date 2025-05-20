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
import { waitFor } from '@app/core/common/time.utils';
import { Point2D } from '@app/core/drawing/drawing';
import { ExtendedMode, Mode } from '@app/core/inference/inference';
import { InferenceResultsService } from '@app/core/inference/inferenceresults.service';
import { Observable, Subject } from 'rxjs';
import { OperationMode } from '../configuration';
import { DeviceFrame } from '../device';
import { DirectImageStreamService } from '../image/direct-image-stream.service';
import { DeviceStreamProvider } from './device-stream-provider';

interface BoundStreamProvider {
  provider: DeviceStreamProvider;
  stream: Observable<DeviceFrame | Error>;
  mode: Mode | ExtendedMode;
  stop: () => void;
}

@Injectable({
  providedIn: 'root',
})
export class DeviceStreamingService {
  private __activeStreamsCache = new Map<String, BoundStreamProvider>();

  private providerByMode = new Map<Mode | ExtendedMode, DeviceStreamProvider>();

  constructor(
    inferenced: InferenceResultsService,
    direct: DirectImageStreamService,
  ) {
    this.providerByMode.set(Mode.InferenceResult, inferenced);
    this.providerByMode.set(Mode.ImageAndInferenceResult, inferenced);

    this.providerByMode.set(Mode.ImageOnly, direct);
    this.providerByMode.set(ExtendedMode.Preview, direct);
  }

  async setupStreaming(
    device_id: string,
    roiOffset: Point2D,
    roiSize: Point2D,
    mode: Mode | ExtendedMode,
    expectedType: OperationMode,
    targetFps: number = 30,
  ) {
    const provider = this.providerByMode.get(mode) as DeviceStreamProvider;
    await provider.init(device_id, roiOffset, roiSize, mode);

    const abortController = new AbortController();
    const stream = new Subject<DeviceFrame | Error>();
    let lastFrame: DeviceFrame | undefined;

    const timingWindow: number[] = [];
    const windowSize = 5;

    const updateDelay = (duration: number): number => {
      timingWindow.push(duration);
      if (timingWindow.length > windowSize) timingWindow.shift();
      const avg = timingWindow.reduce((a, b) => a + b, 0) / timingWindow.length;
      return Math.max(0, 1000 / targetFps - avg);
    };

    async function fetch(): Promise<void> {
      if (abortController.signal.aborted) return;
      const start = performance.now();
      const frame = await provider.getNextFrame(
        device_id,
        mode,
        expectedType,
        abortController.signal,
        lastFrame,
      );
      const end = performance.now();
      if (abortController.signal.aborted) return;

      if (!(frame instanceof Error)) lastFrame = frame;
      const delay = updateDelay(end - start);
      stream.next(frame);

      await waitFor(delay);
      fetch();
    }

    function stop() {
      abortController.abort();
    }

    this.__activeStreamsCache.set(device_id, { provider, stream, stop, mode });
    fetch();
  }

  async getDeviceStreamAsFrames(device_id: string) {
    const boundProvider = this.__activeStreamsCache.get(device_id);
    if (!boundProvider) throw new Error('The device is not streaming');

    return boundProvider.stream;
  }

  async stopStreaming(device_id: string) {
    console.log('Stopping streaming for ' + device_id);
    if (this.__activeStreamsCache.has(device_id)) {
      const boundProvider = this.__activeStreamsCache.get(device_id);
      this.__activeStreamsCache.delete(device_id);
      boundProvider?.stop();
      await boundProvider?.provider.teardown(device_id);
    }
  }

  isDeviceStreaming(device_id: string) {
    return !!this.__activeStreamsCache.get(device_id);
  }

  getStreamingMode(device_id: string) {
    return this.__activeStreamsCache.get(device_id)?.mode;
  }
}
