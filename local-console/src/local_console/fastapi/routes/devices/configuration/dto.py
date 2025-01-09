# Copyright 2024 Sony Semiconductor Solutions Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
from local_console.core.camera.enums import ApplicationType
from local_console.core.camera.enums import UnitScale
from pydantic import BaseModel


class CameraConfigurationDTO(BaseModel):
    image_dir_path: None | str = None
    inference_dir_path: None | str = None
    size: None | int = None
    unit: None | UnitScale = None
    vapp_type: None | ApplicationType = None
    vapp_config_file: None | str = None
    vapp_labels_file: None | str = None
    # Custom app type not supported
