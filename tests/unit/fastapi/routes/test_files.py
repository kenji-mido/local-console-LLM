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
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient
from local_console.core.files.files import FileInfo
from local_console.core.files.files import FilesManager
from local_console.core.files.files import FileType
from local_console.fastapi.routes.files import FileInfoDTO
from local_console.fastapi.routes.files import FileOutDTO
from local_console.fastapi.routes.files import upload_file

from tests.strategies.samplers.files import model_content


@pytest.mark.trio
async def test_upload_file_with_file_manager() -> None:
    file_manager = MagicMock()
    file_info = FileInfo(
        id="1", path=Path("/root/to/sample/file.ext"), type=FileType.FIRMWARE
    )
    file_manager.add_file.return_value = file_info
    type_code = "firmware"
    file_data = b"fake file content"
    file_name = "mockfile.txt"
    file = UploadFile(filename=file_name, file=BytesIO(file_data))

    result = await upload_file(file_manager, type_code, file)

    file_manager.add_file.assert_called_once_with(type_code, file_name, file_data)
    assert result == FileOutDTO(
        file_info=FileInfoDTO(
            file_id=file_info.id, name="file.ext", type_code=file_info.type, size=17
        )
    )


def test_upload_file(fa_client: TestClient, tmp_path) -> None:
    file_info = FileInfo(
        id="1234", path=Path("/root/to/sample/wasm.zip"), type=FileType.MODEL
    )
    fa_client.app.state.file_manager = FilesManager(tmp_path)
    file_content = model_content(b"converted_wasm_application")
    files = {"file": ("wasm.zip", file_content, "application/octet-stream")}

    # Form data
    data = {"type_code": "converted_model"}

    response = fa_client.post("/files", files=files, data=data)

    assert response.status_code == 200

    assert response.json()["result"] == "SUCCESS"
    file_info = response.json()["file_info"]
    assert file_info["file_id"]
    assert file_info["name"] == "wasm.zip"
    assert file_info["type_code"] == "converted_model"
    assert file_info["size"] == 30
