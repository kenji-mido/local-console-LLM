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
from local_console.core.files.files import FilesManager
from local_console.core.files.files_validators import ChainableValidator
from local_console.core.files.values import FileType
from local_console.core.files.values import ZipInfo
from local_console.fastapi.routes.firmwares import FirmwareManifestDTO
from local_console.fastapi.routes.firmwares import FirmwareManifestSWDTO


class FirmwareValidator(ChainableValidator[ZipInfo]):
    def __init__(self, files_manager: FilesManager) -> None:
        super().__init__()
        self._files_manager = files_manager

    def validable(self, info: ZipInfo) -> bool:
        return info.type == FileType.FIRMWARE

    def _read_manifest_info(self, zipfile_info: ZipInfo) -> FirmwareManifestDTO:
        file_bytes: bytes = self._files_manager.read_file_bytes(
            zipfile_info.path / "manifest.json"
        )
        return FirmwareManifestDTO.model_validate_json(file_bytes)

    def _validate_software_list(
        self,
        software_list: list[FirmwareManifestSWDTO],
        list_files_in_firmware: list[str],
    ) -> None:
        set_software_list = {software_info.file_name for software_info in software_list}
        if not set_software_list.issubset(set(list_files_in_firmware)):
            raise ValueError("Firmware in zip file is missing software files")

    def _read_and_validate_manifest_info(
        self, zipfile_info: ZipInfo
    ) -> FirmwareManifestDTO:
        if "manifest.json" not in zipfile_info.list_files:
            raise ValueError("Firmware in zip file is missing manifest.json file")

        return self._read_manifest_info(zipfile_info)

    def validate(self, info: ZipInfo) -> None:
        manifest_info: FirmwareManifestDTO = self._read_and_validate_manifest_info(info)

        self._validate_software_list(manifest_info.sw_list, info.list_files)
