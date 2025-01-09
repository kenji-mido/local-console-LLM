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
import os
import pathlib
import shutil
from tempfile import TemporaryDirectory

import pydantic_core
import pytest
from local_console.core.files.files import FilesManager
from local_console.core.files.files import FileType
from local_console.core.files.files import ZipInfo
from local_console.core.firmware_validator import FirmwareValidator
from local_console.core.firmwares import FirmwareManager
from local_console.core.firmwares import get_firmware_manager

from tests.mocks.files import MockedFileManager
from tests.strategies.samplers.files import ZipInfoSampler


def mocked_firmware() -> FirmwareManager:
    file_manager = MockedFileManager()
    return get_firmware_manager(file_manager)


def mocked_validator(file_manager: FilesManager | None = None) -> FirmwareValidator:
    if not file_manager:
        file_manager = MockedFileManager()
    return FirmwareValidator(file_manager)


def test_validate_zip_info():
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        file_manager = FilesManager(base_path=pathlib.Path(temporary_dir))
        validator = mocked_validator(file_manager)

        firmware_folderpath = os.path.join(temporary_dir, "extracted", "foldername")
        os.makedirs(firmware_folderpath)
        firmware_path = os.path.join(firmware_folderpath, "manifest.json")

        shutil.copyfile(
            f"{pathlib.Path(__file__).parent.resolve()}/manifest.json", firmware_path
        )

        zipfile_info: ZipInfo = ZipInfo(
            id="my_id",
            path=firmware_folderpath,
            type=FileType.FIRMWARE,
            list_files=["manifest.json", "filename1", "filename2"],
        )

        validator.validate(zipfile_info)


def test_read_manifest_info_wrong_structure():
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        file_manager = FilesManager(base_path=pathlib.Path(temporary_dir))
        validator = mocked_validator(file_manager)

        firmware_folderpath = os.path.join(temporary_dir, "extracted", "foldername")
        os.makedirs(firmware_folderpath)
        firmware_path = os.path.join(firmware_folderpath, "manifest.json")

        shutil.copyfile(
            f"{pathlib.Path(__file__).parent.resolve()}/manifest_error.json",
            firmware_path,
        )

        zipfile_info: ZipInfo = ZipInfo(
            id="my_id",
            path=firmware_folderpath,
            type=FileType.FIRMWARE,
            list_files=["manifest.json"],
        )

        with pytest.raises(pydantic_core.ValidationError):
            validator.validate(zipfile_info)


def test_validate_software_list_missing_file():
    validator = mocked_validator()
    validator._files_manager.mock_file_content(
        """
{
  "package_version": "package_version",
  "sw_list": [
    {
      "file_name": "manifest.json",
      "version": "v2.0",
      "type": "type1"
    },
    {
      "file_name": "firmware.bin",
      "version": "v1.0",
      "type": "type2"
    },
    {
      "file_name": "not_in_zip",
      "version": "v1.0",
      "type": "type2"
    }
  ]
}
"""
    )

    zipfile_info = ZipInfoSampler(
        list_files=["manifest.json", "firmware.bin"], type=FileType.FIRMWARE
    ).sample()

    with pytest.raises(ValueError) as e:
        validator.validate(zipfile_info)

    assert str(e.value) == "Firmware in zip file is missing software files"


def test_validate_software_list_extra_files():
    validator = mocked_validator()

    zipfile_info = ZipInfoSampler(
        list_files=["manifest.json", "firmware.bin", "extra_file"],
        type=FileType.FIRMWARE,
    ).sample()

    validator.validate(zipfile_info)


def test_read_and_validate_manifest_info():
    validator = mocked_validator()
    validator._files_manager.mock_file_content(
        """
{
  "package_version": "package_version",
  "sw_list": [
    {
      "file_name": "manifest.json",
      "version": "v2.0",
      "type": "type1"
    },
    {
      "file_name": "firmware.bin",
      "version": "v1.0",
      "type": "type2"
    }
  ]
}
"""
    )

    zipfile_info = ZipInfoSampler(
        type=FileType.FIRMWARE, list_files=["manifest.json", "firmware.bin"]
    ).sample()

    validator.validate(zipfile_info)


def test_read_and_validate_manifest_info_missing_file():
    validator = mocked_validator()

    zipfile_info = ZipInfoSampler(
        list_files=["manifest_wrong_name.json"], type=FileType.FIRMWARE
    ).sample()

    with pytest.raises(ValueError) as e:
        validator.validate(zipfile_info)

    assert str(e.value) == "Firmware in zip file is missing manifest.json file"
