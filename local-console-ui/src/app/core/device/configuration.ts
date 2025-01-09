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

/* Example configuration JSON
{
  "image_dir_path": "/tmp/LocalConsole_p_t2ydha/images",
  "inference_dir_path": "/tmp/LocalConsole_p_t2ydha/inferences",
  "size": "10",
  "unit": "MB",
  "vapp_type": "classification",
  "vapp_config_file": null,
  "vapp_labels_file": null
}
*/
export type OperationMode = 'classification' | 'detection';
export interface Configuration {
  image_dir_path?: string | null;
  inference_dir_path?: string | null;
  size?: number | null;
  unit?: string | null;
  vapp_type?: OperationMode | null;
  vapp_config_file?: string | null;
  vapp_labels_file?: string | null;
}
