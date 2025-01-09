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

/**
 * POST /deploy_configs request body
 */
export interface DeployConfigsIn {
  config_id?: string;
  description?: string;
  models?: DeployConfigModelsIn[] | null;
  edge_system_sw_package?: DeployConfigEdgeSystemIn[] | null;
  edge_apps?: DeployConfigEdgeAppIn[] | null;
}

export interface DeployConfigModelsIn {
  model_id: string;
  model_version_number: string;
}

export interface DeployConfigEdgeSystemIn {
  firmware_id: string;
}

export interface DeployConfigEdgeAppIn {
  edge_app_package_id: string;
  app_name: string;
  app_version: string;
}

/**
 * POST /deploy_configs/{config_id}/apply
 */
export interface DeployConfigApplyIn {
  device_ids: string[];
  description: string;
}

export interface DeployConfigApplyOut {
  result: string;
  deploy_id: string;
}

/**
 * GET /deploy_history response body
 */
export interface DeployHistoriesOut {
  deploy_history: DeployHistoryOut[];
  continuation_token: string | null;
}

export interface DeployHistoryOut {
  deploy_id: string;
  config_id: string;
  from_datetime: string;
  deploy_type: string;
  deploying_cnt: number;
  success_cnt: number;
  fail_cnt: number;
  edge_system_sw_package?: DeployHistoryEdgeSystemOut[];
  models?: DeployHistoryModelsOut[];
  edge_apps?: DeployHistoryEdgeAppsOut[];
  devices: DeployHistoryDevicesOut[];
}

export interface DeployHistoryEdgeSystemOut {
  firmware_id: string;
  firmware_version: string;
  status: DeploymentStatusOut;
}

export interface DeployHistoryModelsOut {
  model_id: string;
  status: DeploymentStatusOut;
}

export interface DeployHistoryEdgeAppsOut {
  app_name: string;
  app_version: string;
  description: string;
  status: DeploymentStatusOut;
}

export interface DeployHistoryDevicesOut {
  device_id: string;
  device_name: string;
}

export enum DeploymentStatusOut {
  Initializing = 'Initializing',
  Running = 'Deploying',
  Success = 'Success',
  Error = 'Fail',
}
