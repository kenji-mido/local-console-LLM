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

@Injectable({
  providedIn: 'root',
})
export class FilesService {
  private filesPathV2 = `${environment.apiV2Url}/files`;
  private modelIdToName: Record<string, string> = {};

  constructor(private http: HttpApiClient) {}

  async createFiles(file: File, type_code: string): Promise<string | null> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('type_code', type_code);

    const result = await this.http.post(`${this.filesPathV2}`, formData, true);
    if (result && result.result === 'SUCCESS' && result.file_info) {
      this.modelIdToName[result.file_info.file_id] = file.name;
      return result.file_info.file_id;
    } else {
      console.error('File upload failed:', result);
    }
    return null;
  }

  getFilename(fileid: string): string {
    return this.modelIdToName[fileid];
  }
}
