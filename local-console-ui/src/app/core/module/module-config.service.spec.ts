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

import { TestBed } from '@angular/core/testing';
import { EnvService } from '../common/environment.service';
import { HttpApiClient } from '../common/http/http';
import { EdgeAppModuleEdgeAppV2 } from './edgeapp';
import { EdgeAppModule } from './module';
import { ModuleConfigService } from './module-config.service';

jest.mock('../common/random.utils', () => ({
  randomString: () => 'mocked-req-id',
}));

jest.mock('../common/time.utils', () => ({
  waitFor: jest.fn().mockResolvedValue(undefined),
}));

class MockHttpApiClient {
  get = jest.fn();
  patch = jest.fn();
}

class MockEnvService {
  getApiUrl = jest.fn().mockReturnValue('https://api.example.com');
}

describe('ModuleConfigService', () => {
  let service: ModuleConfigService;
  let api: MockHttpApiClient;
  let env: MockEnvService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        ModuleConfigService,
        { provide: HttpApiClient, useClass: MockHttpApiClient },
        { provide: EnvService, useClass: MockEnvService },
      ],
    });
    service = TestBed.inject(ModuleConfigService);
    api = TestBed.inject(HttpApiClient) as any;
    env = TestBed.inject(EnvService) as any;
  });

  it('gets module configuration with correct URL', async () => {
    api.get.mockResolvedValue({} as EdgeAppModule);
    await service.getModuleProperty('dev1', 'mod1');
    expect(api.get).toHaveBeenCalledWith(
      'https://api.example.com/devices/dev1/modules/mod1/property',
    );
  });

  it('patches config and confirms application', async () => {
    const config = { req_info: {} } as any;
    let capturedReqId: string | undefined;

    api.patch.mockImplementation((_url, payload) => {
      capturedReqId = payload.configuration.edge_app.req_info.req_id;
      return Promise.resolve();
    });

    api.get.mockImplementation(() => {
      return Promise.resolve({
        state: {
          edge_app: {
            res_info: {
              res_id: capturedReqId,
            },
          },
        },
      });
    });

    await expect(
      service.patchModuleConfiguration('dev1', 'mod1', config),
    ).resolves.toBeUndefined();

    expect(api.patch).toHaveBeenCalled();
    expect(api.get).toHaveBeenCalled();
  });

  it('throws after max pulls if config not applied', async () => {
    const config = { req_info: {} } as EdgeAppModuleEdgeAppV2;
    api.patch.mockResolvedValue(undefined);
    api.get.mockResolvedValue({ property: { state: {} } });
    await expect(
      service.patchModuleConfiguration('dev1', 'mod1', config),
    ).rejects.toThrow(/max attempts exceeded/);
  });

  it('throws on timeout if config not applied fast enough', async () => {
    const config = { req_info: {} } as any;
    api.patch.mockResolvedValue(undefined);

    let time = 0;
    jest
      .spyOn(performance, 'now')
      .mockImplementation(() => (time += 1001 * 10));
    api.get.mockResolvedValue({ property: { state: {} } });

    await expect(
      service.patchModuleConfiguration('dev1', 'mod1', config),
    ).rejects.toThrow(/timeout exceeded/);
  });
});
