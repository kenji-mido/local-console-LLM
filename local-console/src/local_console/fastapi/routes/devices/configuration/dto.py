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
from pathlib import Path
from typing import Any

from local_console.core.camera.enums import ApplicationType
from local_console.core.camera.enums import UnitScale
from local_console.utils.enums import StrEnum
from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator


class StatusType(StrEnum):
    STORAGE_USAGE = "STORAGE_USAGE"
    FOLDER_ERROR = "FOLDER_ERROR"


class Status(BaseModel):
    value: Any = None


class CameraConfigurationDTO(BaseModel):
    auto_deletion: None | bool = Field(
        None,
        description="When enabled, files in the folders will be automatically deleted "
        "to ensure the storage quota is not exceeded. "
        "When disabled, the system will halt inference or image capture once the quota limit is reached.",
    )
    device_dir_path: None | Path = Field(
        None,
        description="Path of directory root where images and inferences will be stored.",
    )
    size: None | int = Field(
        None,
        description="Maximum allowed space (in the specified unit) for the combined size of files within "
        "the device_dir_path. You need to specify in conjunction with unit or directories can grow indefinitely.",
    )
    unit: None | UnitScale = Field(
        None,
        description="Unit of measurement for the size limit (e.g., kilobytes (KB), megabytes(MB) or gigabytes(GB)). "
        "You need to specify in conjunction with size or directories can grow indefinitely.",
    )
    module_file: None | Path = Field(
        None, description="File path to the WASM module of an Edge application."
    )
    ai_model_file: None | Path = Field(
        None, description="File path to the IMX500 network of an Edge application."
    )
    vapp_type: None | ApplicationType = None
    vapp_config_file: None | str = None
    vapp_labels_file: None | str = None
    # Custom app type not supported

    status: dict[StatusType, Status] = {}

    @field_validator("unit", mode="before")
    @classmethod
    def unit_scale_validator(cls, v: str) -> UnitScale | None:
        if not v:
            return None
        return UnitScale.from_value(v)
