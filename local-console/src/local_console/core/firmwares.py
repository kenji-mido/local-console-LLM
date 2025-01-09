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
import logging

from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.files.exceptions import FileNotFound
from local_console.core.files.files import FilesManager
from local_console.core.files.values import FileInfo
from local_console.core.files.values import FileType
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class FirmwareIn(BaseModel):
    firmware_type: OTAUpdateModule
    description: str | None = None
    file_id: str
    version: str


class Firmware(BaseModel):
    firmware_id: str
    info: FirmwareIn
    file: FileInfo


class FirmwareManager:
    def __init__(self, files_manager: FilesManager):
        self._files_manager = files_manager
        self._firmwares: dict[str, Firmware] = dict()

    def register(self, firmware_in: FirmwareIn) -> None:
        file_info: None | FileInfo = self._files_manager.get_file(
            FileType.FIRMWARE, firmware_in.file_id
        )
        if file_info is None:
            raise FileNotFound(firmware_in.file_id)
        self._firmwares[firmware_in.file_id] = Firmware(
            firmware_id=firmware_in.file_id,
            info=firmware_in,
            file=file_info,
        )

    def get_all(self) -> list[Firmware]:
        return sorted(list(self._firmwares.values()), key=lambda x: x.info.file_id)

    def get_by_id(self, firmware_id: str) -> None | Firmware:
        if firmware_id not in self._firmwares:
            return None
        return self._firmwares[firmware_id]


def get_firmware_manager(files_manager: FilesManager) -> FirmwareManager:
    return FirmwareManager(files_manager=files_manager)
