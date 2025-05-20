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

import { TestBed } from '@angular/core/testing';
import { Files } from '@samplers/file';
import { EnvService } from '../common/environment.service';
import { HttpApiClient } from '../common/http/http';
import { FilesService } from './files.service';

class MockHttpApiClient {
  post = jest.fn();
}

describe('FilesService', () => {
  let service: FilesService;
  let httpApiClient: MockHttpApiClient;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        FilesService,
        { provide: HttpApiClient, useClass: MockHttpApiClient },
      ],
    });
    service = TestBed.inject(FilesService);
    httpApiClient = TestBed.inject(
      HttpApiClient,
    ) as unknown as MockHttpApiClient;
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('createFiles', () => {
    const mockFileHandle = Files.sample('test-file.txt');
    const envService = new EnvService();

    it('should return file_id on successful upload', async () => {
      httpApiClient.post.mockResolvedValue({
        result: 'SUCCESS',
        file_info: { file_id: '12345' },
      });

      const fileId = await service.createFiles(
        mockFileHandle,
        'type_code_example',
      );

      expect(fileId).toBe('12345');
      expect(httpApiClient.post).toHaveBeenCalledWith(
        `${envService.getApiUrl()}/files`,
        expect.any(FormData),
        true,
      );

      const formData = httpApiClient.post.mock.calls[0][1] as FormData;
      expect(formData.has('file')).toBe(true);
      const file = formData.get('file') as File;
      expect(file).toBeInstanceOf(File);
      expect(file.name).toBe('test-file.txt');

      expect(formData.has('type_code')).toBe(true);
      const type_code = formData.get('type_code') as string;
      expect(type_code).toBe('type_code_example');
    });

    it('should return null and log error on failed upload', async () => {
      const mockResponse = {
        result: 'FAILURE',
      };
      httpApiClient.post.mockResolvedValue(mockResponse);
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

      const fileId = await service.createFiles(
        mockFileHandle,
        'type_code_example',
      );

      expect(fileId).toBeNull();
      expect(httpApiClient.post).toHaveBeenCalledWith(
        `${envService.getApiUrl()}/files`,
        expect.any(FormData),
        true,
      );
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'File upload failed:',
        mockResponse,
      );

      consoleErrorSpy.mockRestore();
    });
  });
});
