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

import { Injectable } from '@angular/core';
import { HttpParams } from '@angular/common/http';
import { HttpApiClient } from '../common/http/http';
import { environment } from '../../../environments/environment';
import {
  catchError,
  from,
  interval,
  Subject,
  switchMap,
  takeUntil,
} from 'rxjs';
import {
  Classification,
  ClassificationPerception,
  Detection,
  DetectionPerception,
  Inference,
  InferenceItem,
  Mode,
} from './inference';
import { DeviceFrame } from '../device/device';
import { getGenerator } from '@app/layout/pages/data-hub/data-hub.utils';
import { DeviceService } from '../device/device.service';
import { Point2D } from '../drawing/drawing';

@Injectable({
  providedIn: 'root',
})
export class InferenceResultsService {
  private inferencePath = `${environment.apiV2Url}/inferenceresults/devices`;
  private imagePath = `${environment.apiV2Url}/images/devices`;
  private __activeStreamsCache = new Map<String, boolean>();
  private used_colors: [[number, number, number]] = [
    this.getColor(getGenerator()),
  ];

  constructor(
    private http: HttpApiClient,
    private devices: DeviceService,
  ) {}

  async getInference(device_id: string) {
    return await this.http.get<Inference>(
      `${this.inferencePath}/${device_id}?limit=1`,
      undefined,
      false,
    );
  }

  async getInferencesAsFrame(
    device_id: string,
    roiOffset: Point2D,
    roiSize: Point2D,
    intervalTime: number,
    mode: Mode,
  ) {
    const detach$ = new Subject<void>();
    const abortController = new AbortController();

    // Abort the controller when detach$ emits
    detach$.subscribe(() => {
      abortController.abort();
      console.info('Stream aborted for ' + device_id);
    });

    // First start inferencing (idempotent)
    await this.devices.startUploadInferenceData(
      device_id,
      roiOffset,
      roiSize,
      mode,
    );

    // Then we can start loop
    const stream$ = interval(intervalTime).pipe(
      switchMap(() =>
        from(
          this.fetchDeviceFrame(device_id, mode, abortController.signal),
        ).pipe(
          catchError((error) => {
            console.error('Error fetching frame:', error);
            return [new Error('Cannot get device frame', error)];
          }),
          takeUntil(detach$), // Ensure the inner observable completes when detached
        ),
      ),
      takeUntil(detach$), // Ensure the interval completes when detached
    );

    this.__activeStreamsCache.set(device_id, true);
    return {
      stream: stream$,
      detach: async () => {
        const completionSignal = new Promise<void>((complete) => {
          stream$.subscribe({ complete });
        });
        detach$.next();
        detach$.complete();
        console.info('Detaching stream from ' + device_id);
        await completionSignal;
      },
    };
  }

  async stopInferences(device_id: string) {
    this.__activeStreamsCache.set(device_id, false);
    console.log('Stopping inferences for ' + device_id);
    return await this.devices.stopUploadInferenceData(device_id);
  }

  isDeviceStreaming(device_id: string) {
    return !!this.__activeStreamsCache.get(device_id);
  }

  private async fetchDeviceFrame(
    device_id: string,
    mode: Mode,
    abortSignal: AbortSignal,
  ): Promise<DeviceFrame | Error> {
    const aborted = new Error('ABORTED');
    try {
      if (abortSignal.aborted) return aborted;
      let image = null;
      let parsedInference = null;

      if (mode === Mode.ImageAndInferenceResult) {
        const rawInference = await this.getInference(device_id);
        if (abortSignal.aborted) return aborted;

        const infDef = rawInference.data[0].inference_result.Inferences[0];
        parsedInference = await this.convertToJson(device_id, infDef.O);
        if (abortSignal.aborted) return aborted;

        const hits =
          (<DetectionPerception>parsedInference.perception)
            .object_detection_list ||
          (<ClassificationPerception>parsedInference.perception)
            .classification_list;
        this.fillInInferenceData(hits);

        image = await this.getInferenceImage(device_id, infDef.T + '.jpg');
        if (abortSignal.aborted) return aborted;
      } else if (mode === Mode.ImageOnly) {
        const imageName = await this.getLatestImageName(device_id);
        if (abortSignal.aborted) return aborted;

        image = await this.getInferenceImage(device_id, imageName);
        if (abortSignal.aborted) return aborted;
      } else {
        console.error(`Mode ${mode} not supported`);
        return new Error(`Mode ${mode} not supported`);
      }

      return { image, inference: parsedInference } as DeviceFrame;
    } catch (error) {
      return new Error('Cannot get device frame', error as Error);
    }
  }

  async convertToJson(device_id: string, flatbuffer_payload: string) {
    let queryParams = new HttpParams();
    queryParams = queryParams.append('flatbuffer_payload', flatbuffer_payload);
    return await this.http
      .get<
        Classification | Detection
      >(`${this.inferencePath}/${device_id}/json`, queryParams, false)
      .catch();
  }

  async getInferenceImage(device_id: string, name: string) {
    const bytes = await this.http.getblob(
      `${this.imagePath}/${device_id}/image/${name}`,
      undefined,
      false,
    );
    return 'data:image/jpeg;base64,' + this.arrayBufferToBase64(bytes);
  }

  async getLatestImageName(device_id: string) {
    return (
      await this.http.get(
        `${this.imagePath}/${device_id}/directories?limit=1`,
        undefined,
        false,
      )
    ).data[0].name;
  }

  private fillInInferenceData(hits: InferenceItem[]) {
    // Reset random for consistent colors
    const prng = getGenerator();
    hits.forEach((item) => {
      item.score = Math.round(item.score * 100 * 100) / 100;
      if (this.used_colors.length - 1 < item.class_id) {
        this.used_colors.push(this.getColor(prng));
      }
      item.color = this.used_colors[item.class_id];
      item.label = 'Class ' + item.class_id;
    });
  }

  private getColor(prng: () => number): [number, number, number] {
    return [
      Math.floor(prng() * 256),
      Math.floor(prng() * 256),
      Math.floor(prng() * 256),
    ];
  }

  private arrayBufferToBase64(buffer: ArrayBuffer): string {
    const uint8Array = new Uint8Array(buffer);

    let binaryString = '';
    for (let i = 0; i < uint8Array.length; i++) {
      binaryString += String.fromCharCode(uint8Array[i]);
    }

    return btoa(binaryString);
  }
}
