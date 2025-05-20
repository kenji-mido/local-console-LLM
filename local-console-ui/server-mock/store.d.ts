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

import { DeviceListV2 } from '@app/core/device/device';
import { NIC } from '@app/core/nic/nic';

export class LocalDeployHistories implements DeployHistoriesOut {
  constructor(
    public deploy_history: DeployHistoryOut[],
    public continuation_token: string | null,
  ) {}
}

export interface Store {
  devices: DeviceListV2;
  deployments: LocalDeployHistories;
  streaming_image_index: { [key: string]: number };
  configurations: { [key: string]: Configuration };
  nics: NIC[];
  configPatchReqIds: Map<string, string>;
}
