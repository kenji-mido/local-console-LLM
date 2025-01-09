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
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from typing import Self
from unittest.mock import MagicMock
from unittest.mock import patch

from local_console.core.files.files import FilesManager
from local_console.core.files.values import FileInfo
from local_console.core.files.values import FileType

MANIFEST_SAMPLE = """
{
  "package_version": "package_version",
  "sw_list": [
    {
      "file_name": "firmware.bin",
      "version": "v2.0",
      "type": "type1"
    }
  ]
}
"""


class MockedFileManager(MagicMock):
    def __init__(self, *args: Any, **kw: Any) -> None:
        super().__init__(spec=FilesManager, *args, **kw)
        self._patch()
        self.mocked_filed = MANIFEST_SAMPLE

    def _patch(self) -> Self:
        patch.object(self, "read_file_bytes", wraps=self.read_file_bytes)

    def mock_file_content(self, content: str) -> None:
        self.mocked_filed = content

    def read_file_bytes(self, path: Path) -> bytes:
        return self.mocked_filed.encode("utf-8")

    def get_file(self, file_type: FileType, file_id: str) -> None | FileInfo:
        if self.mocked_filed is None:
            return None

        return FileInfo(
            id=file_id,
            path=self.mocked_filed,
            type=file_type,
        )


@contextmanager
def mock_files_manager() -> Generator[MockedFileManager, None, None]:
    mocked = MockedFileManager()
    with patch("local_console.core.files.files.FilesManager", mocked):
        yield mocked
