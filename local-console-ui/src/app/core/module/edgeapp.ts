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

import { DTDLReqInfoV2, DTDLResInfoV2 } from './dtdl';

// Module: edge app
//  - configuration: TODO: Spec unknown
//  - state
export interface EdgeAppModuleConfigurationV2 {
  edge_app?: EdgeAppModuleEdgeAppV2;
}

// Module: edge app
// configuration:
// - edge_app
export interface EdgeAppModuleEdgeAppV2 {
  req_info?: DTDLReqInfoV2;
  res_info?: DTDLResInfoV2;
  common_settings?: EdgeAppModuleEdgeAppCommonSettingsV2;
  custom_settings?: EdgeAppModuleEdgeAppCustomSettingsV2;
}

export interface EdgeAppModuleEdgeAppCustomSettingsV2 {
  ai_models?: {
    one_pass_model?: {
      parameters?: {
        threshold?: number;
        input_width?: number;
        input_height?: number;
        max_detections?: number;
        dnn_output_detections?: number;
      };
      ai_model_bundle_id?: string;
    };
  };
}

export interface EdgeAppModuleEdgeAppCommonSettingsV2 {
  log_level?: number;
  pq_settings?: EdgeAppModuleEdgeAppPQSettingsV2;
  port_settings?: EdgeAppModuleEdgeAppPortSettingsV2;
  process_state?: number;
  codec_settings?: {
    format?: number;
  };
  upload_interval?: number;
  inference_settings?: {
    number_of_iterations?: number;
  };
  number_of_inference_per_message?: number;
}

export interface EdgeAppModuleEdgeAppPortSettingsV2 {
  metadata?: {
    path?: string;
    method?: number;
    enabled?: boolean;
    endpoint?: string;
    storage_name?: string;
  };
  input_tensor?: {
    path?: string;
    method?: number;
    enabled?: boolean;
    endpoint?: string;
    storage_name?: string;
  };
}

export interface EdgeAppModuleEdgeAppPQSettingsV2 {
  frame_rate?: {
    num?: number;
    denom?: number;
  };
  digital_zoom?: number;
  auto_exposure?: {
    max_gain?: number;
    convergence_speed?: number;
    max_exposure_time?: number;
    min_exposure_time?: number;
  };
  exposure_mode?: number;
  image_cropping?: {
    top?: number;
    left?: number;
    width?: number;
    height?: number;
  };
  image_rotation?: number;
  ev_compensation?: number;
  manual_exposure?: {
    gain?: number;
    exposure_time?: number;
  };
  camera_image_flip?: {
    flip_vertical?: number;
    flip_horizontal?: number;
  };
  camera_image_size?: {
    width?: number;
    height?: number;
    scaling_policy?: number;
  };
  auto_white_balance?: {
    convergence_speed?: number;
  };
  white_balance_mode?: number;
  ae_anti_flicker_mode?: number;
  manual_white_balance_gain?: {
    red?: number;
    blue?: number;
  };
  manual_white_balance_preset?: {
    color_temperature?: number;
  };
}

export interface EdgeAppModuleStateV2 {
  edge_app?: EdgeAppModuleEdgeAppV2;
}
