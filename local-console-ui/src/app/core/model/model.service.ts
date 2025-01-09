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
import { HttpApiClient } from '../common/http/http';
import { environment } from '../../../environments/environment';
import { FilesService } from '../file/files.service';

@Injectable({
  providedIn: 'root',
})
export class ModelService {
  private pathV2 = `${environment.apiV2Url}/models`;
  private modelIdToFileId: Record<string, string> = {};

  constructor(
    private http: HttpApiClient,
    private fileService: FilesService,
  ) {}

  async createModel(model_id: string, file_id: string): Promise<string | null> {
    try {
      const result = await this.http.post(
        `${this.pathV2}`,
        { model_id: model_id, model_file_id: file_id },
        false,
      );
      if (result && result.result === 'SUCCESS') {
        this.modelIdToFileId[model_id] = file_id;
        return model_id;
      } else {
        console.error('File upload failed:', result);
      }
    } catch (error) {
      console.error('Error while parsing result:', error);
    }
    return null;
  }

  getFileName(modelId: string): string {
    return this.fileService.getFilename(this.modelIdToFileId[modelId]);
  }
}
