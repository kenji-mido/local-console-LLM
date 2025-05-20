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
import { EnvService } from '../common/environment.service';
import { HttpApiClient } from '../common/http/http';
import { FilesService } from '../file/files.service';
import { FirmwareV2 } from './firmware';

@Injectable({
  providedIn: 'root',
})
export class FirmwareService {
  constructor(
    private http: HttpApiClient,
    private fileService: FilesService,
    private envService: EnvService,
  ) {}

  get firmwaresV2Path() {
    return `${this.envService.getApiUrl()}/firmwares`;
  }

  async createFirmwareV2(payload: FirmwareV2) {
    try {
      const result = await this.http.post(
        this.firmwaresV2Path,
        {
          firmware_type: payload.firmware_type,
          file_id: payload.file_id,
          version: payload.version,
        },
        false,
      );
      if (result && result.result === 'SUCCESS') {
        return payload.file_id;
      } else {
        console.error('File upload failed:', result);
      }
    } catch (error) {
      console.error('Error while parsing result:', error);
    }
    return null;
  }

  getFileName(firmwareId: string): string {
    return this.fileService.getFilename(firmwareId);
  }
}
