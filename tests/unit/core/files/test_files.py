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
import json
import os
import pathlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from local_console.core.files.files import FileInfo
from local_console.core.files.files import FilesManager
from local_console.core.files.files import FileType
from local_console.core.files.files import temporary_files_manager
from local_console.core.files.files import ZipInfo
from local_console.utils.validation import AOT_XTENSA_HEADER

from tests.strategies.samplers.files import app_content
from tests.strategies.samplers.files import model_content


def test_invalidvalid_types() -> None:
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        file_content = b"just example"
        file_name = "app.zip"
        base_path = Path(temporary_dir)
        manager = FilesManager(base_path=base_path)
        with pytest.raises(ValueError) as error:
            manager.add_file("invalid_type", file_name, file_content)

        assert str(error.value) == "'invalid_type' is not a valid FileType"


@pytest.mark.parametrize("type", FileType)
def test_create_app_file(type: FileType) -> None:
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        file_content = b"just example"
        if type in [FileType.MODEL, FileType.MODEL_RAW]:
            file_content = model_content()
        if type in [FileType.APP, FileType.APP_RAW]:
            file_content = bytes(AOT_XTENSA_HEADER)

        file_name = "app.bin"
        base_path = Path(temporary_dir)
        manager = FilesManager(base_path=base_path)
        file_info: FileInfo = manager.add_file(type.value, file_name, file_content)

        assert file_info.path == base_path / type / file_info.id / "file" / file_name
        assert file_info.path.read_bytes() == file_content
        assert file_info.type == type


@patch("local_console.core.files.files.random_id")
def test_overwrite_file_content(random_id: MagicMock) -> None:
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        file_id = "1"
        random_id.return_value = file_id
        type = FileType.APP
        base_path = Path(temporary_dir)
        file_name = "app.zip"
        expected_path: Path = base_path / type / file_id / "file" / file_name
        expected_path.parent.mkdir(parents=True)
        expected_path.write_text("Previous content")
        file_content = bytes(AOT_XTENSA_HEADER) + b"new content"

        manager = FilesManager(base_path=base_path)
        manager.validate_before_saving = lambda x: None
        file_info: FileInfo = manager.add_file(type.value, file_name, file_content)

        assert file_info.path.read_bytes() == file_content
        assert file_info.id == file_id


def test_temporal_file_manager() -> None:
    file_info: FileInfo | None = None
    with temporary_files_manager() as files_manager:
        file_content = model_content()
        file_info = files_manager.add_file(FileType.MODEL, "model.bin", file_content)
        assert file_info.path.exists()

    assert not file_info.path.exists()


def test_get_file() -> None:
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        base_path = Path(temporary_dir)

        manager = FilesManager(base_path=base_path)
        file_info: FileInfo = manager.add_file(
            raw_type=FileType.FIRMWARE,
            file_name="firmware.bin",
            file_content=b"firmware_content",
        )

        result = manager.get_file(file_type=FileType.FIRMWARE, file_id=file_info.id)

        assert result == file_info


def test_get_file_wrong_type() -> None:
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        base_path = Path(temporary_dir)

        manager = FilesManager(base_path=base_path)
        file_info: FileInfo = manager.add_file(
            raw_type=FileType.FIRMWARE,
            file_name="firmware.fpk",
            file_content=b"firmware_content",
        )

        result = manager.get_file(file_type=FileType.APP, file_id=file_info.id)

        assert result is None


def test_get_file_not_found() -> None:
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        base_path = Path(temporary_dir)

        manager = FilesManager(base_path=base_path)

        result = manager.get_file(file_type=FileType.APP, file_id="my_id")

        assert result is None


def test_get_file_two_files() -> None:
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        base_path = Path(temporary_dir)

        manager = FilesManager(base_path=base_path)
        file_info: FileInfo = manager.add_file(
            raw_type=FileType.FIRMWARE,
            file_name="firmware1.bin",
            file_content=b"firmware_content",
        )

        dir_path = manager.get_file_rootdir(
            file_type=FileType.FIRMWARE, file_id=file_info.id
        )
        with open(dir_path / "firmware2.bin", "w") as f:
            f.write("firmware_content")

        with pytest.raises(ValueError) as error:
            manager.get_file(file_type=FileType.FIRMWARE, file_id=file_info.id)

        assert (
            str(error.value)
            == f"There is more than one file with type {FileType.FIRMWARE} and id {file_info.id}."
        )


def test_get_file_no_file():
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        base_path = Path(temporary_dir)

        manager = FilesManager(base_path=base_path)
        file_id = "my_id"
        file_type = FileType.APP

        dir_path = manager.get_file_rootdir(file_type=file_type, file_id=file_id)
        os.makedirs(dir_path)

        with pytest.raises(ValueError) as e:
            manager.get_file(file_type=file_type, file_id=file_id)

        assert (
            str(e.value) == f"There is no file with type {file_type} and id {file_id}"
        )


def test_unzip():
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        base_path = Path(temporary_dir)
        manager = FilesManager(base_path=base_path, save_check=lambda x: None)

        file_type = FileType.FIRMWARE
        file_name = "file_name.zip"

        with open(
            f"{pathlib.Path(__file__).parent.resolve()}/../test_unzip.zip", "rb"
        ) as f:
            file_content = f.read()

        # Read test_unzip.zip as bytes
        file_info = manager.add_file(
            raw_type=file_type, file_name=file_name, file_content=file_content
        )

        unzipped_file_info: ZipInfo = manager.unzip(file_info)

        assert unzipped_file_info.id == file_info.id
        assert os.path.exists(unzipped_file_info.path)
        assert set(os.listdir(unzipped_file_info.path)) == {
            "firmware.bin",
            "manifest.json",
        }


def test_unzip_nozip():
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        base_path = Path(temporary_dir)
        manager = FilesManager(base_path=base_path)

        file_info: FileInfo = manager.add_file(
            raw_type=FileType.APP_RAW,
            file_name="firmware.zip",
            file_content=app_content(),
        )

        with pytest.raises(ValueError) as e:
            manager.unzip(file_info)

        assert (
            str(e.value) == f"File identified by FileInfo {file_info} is not a zip file"
        )


def test_unzip_nofile():
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        base_path = Path(temporary_dir)
        manager = FilesManager(base_path=base_path)

        file_id = "my_id"
        file_type = FileType.MODEL_RAW
        file_path = (
            manager.get_zip_rootdir(file_type=file_type, file_id=file_id)
            / "filename.zip"
        )
        file_info = FileInfo(id=file_id, type=file_type, path=file_path)

        with pytest.raises(FileNotFoundError) as e:
            manager.unzip(file_info)

        assert str(e.value) == f"File identified by FileInfo {file_info} does not exist"


def test_unzip_two_files():
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        base_path = Path(temporary_dir)
        manager = FilesManager(base_path=base_path, save_check=lambda x: None)

        file_type = FileType.FIRMWARE
        file_name = "test_unzip.zip"

        with open(
            f"{pathlib.Path(__file__).parent.resolve()}/../test_unzip.zip", "rb"
        ) as f:
            file_content = f.read()

        # Read test_unzip.zip as bytes
        file_info = manager.add_file(
            raw_type=file_type, file_name=file_name, file_content=file_content
        )

        unzipped_file_info_1: ZipInfo = manager.unzip(file_info)
        unzipped_file_info_2: ZipInfo = manager.unzip(file_info)

        assert unzipped_file_info_1 == unzipped_file_info_2
        assert unzipped_file_info_1.id == file_info.id
        assert os.path.exists(unzipped_file_info_1.path)
        assert set(os.listdir(unzipped_file_info_1.path)) == {
            "firmware.bin",
            "manifest.json",
        }


def test_validator_error() -> None:
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        failing_validator = MagicMock()
        expected_error = ValueError("The file info is not correct")
        failing_validator.side_effect = expected_error
        file_manager = FilesManager(Path(temporary_dir), save_check=failing_validator)

        with pytest.raises(ValueError) as error:
            file_manager.add_file(FileType.MODEL_RAW, "will.fail", b"for sure")

        failing_validator.assert_called_once()
        assert error.value == expected_error


def test_read_file_bytes():
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        file_manager = FilesManager(Path(temporary_dir))

        target_content = {
            "package_version": "package_version",
            "sw_list": [
                {"file_name": "filename1", "version": "v2.0", "type": "type1"},
                {"file_name": "filename2", "version": "v1.0", "type": "type2"},
            ],
        }
        expected_str = json.dumps(target_content, indent=2) + "\n"
        expected_bytes = expected_str.encode("utf-8")

        manifest_path = f"{pathlib.Path(__file__).parent.resolve()}/../manifest.json"
        file_content: bytes = file_manager.read_file_bytes(Path(manifest_path))

        assert file_content == expected_bytes


def test_read_file_bytes_no_file():
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        file_manager = FilesManager(Path(temporary_dir))

        manifest_path = (
            f"{pathlib.Path(__file__).parent.resolve()}/manifest_no_exists.json"
        )

        with pytest.raises(ValueError) as e:
            file_manager.read_file_bytes(Path(manifest_path))

        assert str(e.value) == f"File in path '{manifest_path}' does not exist"


def test_get_files_by_type():
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        file_manager = FilesManager(Path(temporary_dir))

        total_list_files = [
            FileInfo(
                id="file_id_1",
                path=f"{temporary_dir}/{FileType.APP_RAW}/file_id_1/file/filename.ext",
                type=FileType.APP_RAW,
            ),
            FileInfo(
                id="file_id_2",
                path=f"{temporary_dir}/{FileType.MODEL_RAW}/file_id_2/file/filename.ext",
                type=FileType.MODEL_RAW,
            ),
            FileInfo(
                id="file_id_3",
                path=f"{temporary_dir}/{FileType.FIRMWARE}/file_id_3/file/filename.ext",
                type=FileType.FIRMWARE,
            ),
            FileInfo(
                id="file_id_4",
                path=f"{temporary_dir}/{FileType.APP_RAW}/file_id_4/file/filename.ext",
                type=FileType.APP_RAW,
            ),
        ]

        for file_info in total_list_files:
            file_info.path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_info.path, "w") as f:
                f.write("content")

        expected_list_files = [
            file_info
            for file_info in total_list_files
            if file_info.type == FileType.APP_RAW
        ]

        list_files: list[FileInfo] = file_manager.get_files_by_type(FileType.APP_RAW)

        assert sorted(list_files, key=lambda x: x.id) == sorted(
            expected_list_files, key=lambda x: x.id
        )


def test_get_files_by_type_no_file():
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        file_manager = FilesManager(Path(temporary_dir))

        total_list_files = [
            FileInfo(
                id="file_id_1",
                path=f"{temporary_dir}/{FileType.APP_RAW}/file_id_1/file/filename.ext",
                type=FileType.APP_RAW,
            ),
            FileInfo(
                id="file_id_2",
                path=f"{temporary_dir}/{FileType.MODEL_RAW}/file_id_2/file/filename.ext",
                type=FileType.MODEL_RAW,
            ),
        ]

        for file_info in total_list_files:
            file_info.path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_info.path, "w") as f:
                f.write("content")

        list_files: list[FileInfo] = file_manager.get_files_by_type(FileType.FIRMWARE)

        assert len(list_files) == 0
