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
import { EnvService } from '../common/environment.service';
import { HttpApiClient } from '../common/http/http';
import { randomString } from '../common/random.utils';
import { waitFor } from '../common/time.utils';
import {
  EdgeAppModuleConfigurationPatchV2,
  EdgeAppModuleEdgeAppV2,
} from './edgeapp';
import { EdgeAppModuleProperty } from './module';

export const PATCH_CONFIGURATION_TIMEOUT = 60000;
export const PATCH_CONFIGURATION_MAX_PULLS = 100;
export const PATCH_CONFIGURATION_POLL_DELAY = 600;

export class PatchConfigurationTimeoutError extends Error {
  constructor(timeout: number) {
    super(
      `Could not verify configuration application. Reason: timeout exceeded (${timeout})`,
    );
    this.name = 'PatchConfigurationTimeoutError';
  }
}

export class PatchConfigurationMaxAttemptsError extends Error {
  constructor(attempts: number) {
    super(
      `Could not verify configuration application. Reason: max attempts exceeded (${attempts})`,
    );
    this.name = 'PatchConfigurationMaxAttemptsError';
  }
}

@Injectable({
  providedIn: 'root',
})
export class ModuleConfigService {
  constructor(
    private api: HttpApiClient,
    private envService: EnvService,
  ) {}

  async getModuleProperty(deviceId: string, moduleId: string) {
    return await this.api.get<EdgeAppModuleProperty>(
      this.getUrl(deviceId, moduleId),
    );
  }

  async patchModuleConfiguration(
    deviceId: string,
    moduleId: string,
    config: EdgeAppModuleEdgeAppV2,
  ) {
    const reqId = randomString();
    const payload: EdgeAppModuleConfigurationPatchV2 = {
      configuration: {
        edge_app: {
          ...config,
          req_info: {
            ...config.req_info,
            req_id: reqId,
          },
        },
      },
    };
    await this.api.patch(this.getUrl(deviceId, moduleId), payload);
    const start = performance.now();
    let i = 0;
    for (
      ;
      i < PATCH_CONFIGURATION_MAX_PULLS &&
      performance.now() - start < PATCH_CONFIGURATION_TIMEOUT;
      i++
    ) {
      const moduleProperty = await this.getModuleProperty(deviceId, moduleId);
      if (moduleProperty?.state?.edge_app?.res_info?.res_id === reqId) {
        return;
      }
      // Give the device a short window to process and report the new reqID
      await waitFor(PATCH_CONFIGURATION_POLL_DELAY);
    }

    if (i === PATCH_CONFIGURATION_MAX_PULLS) {
      throw new PatchConfigurationMaxAttemptsError(
        PATCH_CONFIGURATION_MAX_PULLS,
      );
    }
    throw new PatchConfigurationTimeoutError(PATCH_CONFIGURATION_TIMEOUT);
  }

  private getUrl(deviceId: string, moduleId: string): string {
    return `${this.envService.getApiUrl()}/devices/${deviceId}/modules/${moduleId}/property`;
  }
}
