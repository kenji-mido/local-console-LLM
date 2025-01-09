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
import { HttpApiClient } from '../common/http/http';
import { environment } from '../../../environments/environment';
import { FirmwareService } from './firmware.service';
import { FirmwareV2 } from './firmware';

class MockHttpApiClient {
  post = jest.fn();
}

describe('FirmwareService', () => {
  let service: FirmwareService;
  let httpApiClient: MockHttpApiClient;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        FirmwareService,
        { provide: HttpApiClient, useClass: MockHttpApiClient },
      ],
    });
    service = TestBed.inject(FirmwareService);
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

  describe('createFirmware', () => {
    const firmware_payload: FirmwareV2 = {
      firmware_type: 'ApFw',
      file_id: 'fw_id',
      version: 'version',
    };
    const apiUrl = `${environment.apiV2Url}/firmwares`;

    it('should return file_id on successful firmware creation', async () => {
      const mockResponse = {
        result: 'SUCCESS',
      };
      httpApiClient.post.mockResolvedValue(mockResponse);

      const result = await service.createFirmwareV2(firmware_payload);

      expect(result).toBe(firmware_payload.file_id);
      expect(httpApiClient.post).toHaveBeenCalledWith(
        apiUrl,
        firmware_payload,
        false,
      );
    });

    it('should return null and log error on failed firmware creation', async () => {
      const mockResponse = {
        result: 'FAILURE',
        message: 'Invalid file ID',
      };
      httpApiClient.post.mockResolvedValue(mockResponse);

      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

      const result = await service.createFirmwareV2(firmware_payload);

      expect(result).toBeNull();
      expect(httpApiClient.post).toHaveBeenCalledWith(
        apiUrl,
        firmware_payload,
        false,
      );
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'File upload failed:',
        mockResponse,
      );

      consoleErrorSpy.mockRestore();
    });

    it('should return null and log error on exception during firmware creation', async () => {
      const mockError = new Error('Network error');
      httpApiClient.post.mockRejectedValue(mockError);

      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

      const result = await service.createFirmwareV2(firmware_payload);

      expect(result).toBeNull();
      expect(httpApiClient.post).toHaveBeenCalledWith(
        apiUrl,
        firmware_payload,
        false,
      );
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Error while parsing result:',
        mockError,
      );

      consoleErrorSpy.mockRestore();
    });
  });
});
