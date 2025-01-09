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
import os
import zipfile
from collections.abc import Callable
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from local_console.core.files.files_validators import save_validator
from local_console.core.files.files_validators import ValidableFileInfo
from local_console.core.files.values import FileInfo
from local_console.core.files.values import FileType
from local_console.core.files.values import ZipInfo
from local_console.utils.random import random_id

logger = logging.getLogger(__name__)


class FilesManager:
    def __init__(
        self,
        base_path: Path,
        save_check: Callable[[ValidableFileInfo], None] = save_validator(),
    ) -> None:
        self.base_path = base_path
        self.validate_before_saving = save_check

    def read_file_bytes(self, path: Path) -> bytes:
        try:
            with open(path, "rb") as f:
                return f.read()
        except FileNotFoundError:
            raise ValueError(f"File in path '{path}' does not exist")

    def get_file_rootdir(self, file_id: str, file_type: FileType) -> Path:
        return self.base_path / file_type / file_id / "file"

    def get_zip_rootdir(self, file_id: str, file_type: FileType) -> Path:
        return self.base_path / file_type / file_id / "extracted"

    def add_file(self, raw_type: str, file_name: str, file_content: bytes) -> FileInfo:
        file_type: FileType = FileType(raw_type)
        file_id = random_id()
        path = self.get_file_rootdir(file_id=file_id, file_type=file_type) / file_name
        pre_save_info = ValidableFileInfo(
            id=file_id, path=path, type=file_type, content=file_content
        )
        self.validate_before_saving(pre_save_info)
        logger.debug(f"File {file_type} will be saved on {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(file_content)
        return pre_save_info.to_file_info()

    def get_file(self, file_type: FileType, file_id: str) -> None | FileInfo:
        """
        Return the file uniquely identified by file type and file id, in FileInfo format
        """
        dir_path = self.get_file_rootdir(file_id=file_id, file_type=file_type)

        try:
            list_files_type_id = os.listdir(dir_path)
        except FileNotFoundError:
            return None

        if len(list_files_type_id) > 1:
            raise ValueError(
                f"There is more than one file with type {file_type} and id {file_id}."
            )
        elif len(list_files_type_id) == 0:
            raise ValueError(f"There is no file with type {file_type} and id {file_id}")

        file_path = os.path.join(dir_path, list_files_type_id[0])

        return FileInfo(id=file_id, path=Path(file_path), type=file_type)

    def unzip(self, file_info: FileInfo) -> ZipInfo:
        """
        Unzip the file in file_info and return the path to the resulting directory
        """
        if not os.path.exists(file_info.path):
            raise FileNotFoundError(
                f"File identified by FileInfo {file_info} does not exist"
            )

        output_path = self.get_zip_rootdir(
            file_id=file_info.id, file_type=file_info.type
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(file_info.path, "r") as zip_ref:
                zip_ref.extractall(output_path)
        except zipfile.BadZipFile:
            raise ValueError(
                f"File identified by FileInfo {file_info} is not a zip file"
            )

        file_path = output_path / os.listdir(output_path)[0]

        list_files_inside = os.listdir(file_path)

        return ZipInfo(
            id=file_info.id,
            path=file_path,
            type=file_info.type,
            list_files=list_files_inside,
        )

    def get_files_by_type(self, file_type: FileType) -> list[FileInfo]:
        return_list: list[FileInfo] = []
        filetype_folderpath: Path = self.base_path / file_type
        for file_id_folderpath in filetype_folderpath.glob("*"):
            file_folderpath: Path = file_id_folderpath / "file"
            filepath: Path = file_folderpath / list(file_folderpath.glob("*"))[0]
            return_list.append(
                FileInfo(
                    id=file_id_folderpath.stem,
                    path=filepath,
                    type=file_type,
                )
            )

        return return_list


def create_files_manager(base_path: Path) -> FilesManager:
    return FilesManager(base_path)


@contextmanager
def temporary_files_manager() -> Generator[FilesManager, None, None]:
    with TemporaryDirectory(prefix="local_console") as temp:
        logger.info(f"New temporal file manager created on {temp}")
        yield create_files_manager(Path(temp))
