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

from local_console.utils.enums import StrEnum
from pydantic import BaseModel
from pydantic import field_validator


class FileType(StrEnum):
    MODEL_RAW = "non_converted_model"
    MODEL = "converted_model"
    FIRMWARE = "firmware"
    APP_RAW = "edge_app"
    APP = "edge_app_dtdl"


class FileInfo(BaseModel):
    id: str
    path: Path
    type: FileType


class ZipInfo(FileInfo):
    list_files: list[str]

    @field_validator("path")
    @classmethod
    def has_right_format(cls, v: Path) -> Path:
        if v.parent.stem != "extracted":
            raise ValueError(
                "Path of a zip file must be located in a folder called 'extracted'. E.g. /path/to/extracted/filename"
            )
        return v
