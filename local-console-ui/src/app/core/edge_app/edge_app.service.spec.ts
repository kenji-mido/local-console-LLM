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
import { EdgeAppService } from './edge_app.service';

class MockHttpApiClient {
  post = jest.fn();
}

describe('EdgeAppService', () => {
  let service: EdgeAppService;
  let httpApiClient: MockHttpApiClient;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        EdgeAppService,
        { provide: HttpApiClient, useClass: MockHttpApiClient },
      ],
    });
    service = TestBed.inject(EdgeAppService);
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

  describe('createEdgeApp', () => {
    const appName = 'Test App';
    const fileId = '12345';
    const apiUrl = `${environment.apiV2Url}/edge_apps`;

    it('should return file_id on successful edge app creation', async () => {
      const mockResponse = {
        result: 'SUCCESS',
      };
      httpApiClient.post.mockResolvedValue(mockResponse);

      const result = await service.createEdgeApp(appName, fileId);

      expect(result).toBe(fileId);
      expect(httpApiClient.post).toHaveBeenCalledWith(
        apiUrl,
        { app_name: appName, edge_app_package_id: fileId },
        false,
      );
    });

    it('should return null and log error on failed edge app creation', async () => {
      const mockResponse = {
        result: 'FAILURE',
        message: 'Invalid file ID',
      };
      httpApiClient.post.mockResolvedValue(mockResponse);

      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

      const result = await service.createEdgeApp(appName, fileId);

      expect(result).toBeNull();
      expect(httpApiClient.post).toHaveBeenCalledWith(
        apiUrl,
        { app_name: appName, edge_app_package_id: fileId },
        false,
      );
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'File upload failed:',
        mockResponse,
      );

      consoleErrorSpy.mockRestore();
    });

    it('should return null and log error on exception during edge app creation', async () => {
      const mockError = new Error('Network error');
      httpApiClient.post.mockRejectedValue(mockError);

      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

      const result = await service.createEdgeApp(appName, fileId);

      expect(result).toBeNull();
      expect(httpApiClient.post).toHaveBeenCalledWith(
        apiUrl,
        { app_name: appName, edge_app_package_id: fileId },
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
