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
from unittest.mock import Mock

import pytest
import requests
from local_console.servers.webserver import SyncWebserver

logger = logging.getLogger(__name__)


@pytest.fixture
def sync_webserver(tmp_path):
    with SyncWebserver(tmp_path) as server:
        yield server


def test_happy_path(sync_webserver):
    file_name = "testfile.txt"
    url = f"http://localhost:{sync_webserver.port}/{file_name}"
    data = b"This is a test file"

    recvd_data = b""
    recvd_path = ""

    def put_callback(data: bytes, path: str) -> None:
        nonlocal recvd_data, recvd_path
        recvd_data = data
        recvd_path = path

    sync_webserver.on_incoming = put_callback
    sync_webserver.max_upload_size = 1024

    # Upload file
    response = requests.put(url, data=data)
    assert response.status_code == 200

    # Verify the callback was effective
    assert recvd_data == data
    assert recvd_path == f"/{file_name}"


def test_size_limit_hit(sync_webserver):
    file_name = "testfile.txt"
    url = f"http://localhost:{sync_webserver.port}/{file_name}"
    data = b"This is a test file"

    content = b""

    def put_callback(data: bytes) -> None:
        nonlocal content
        content = data

    sync_webserver.on_incoming = Mock()
    sync_webserver.max_upload_size = 2

    # Upload file
    response = requests.put(url, data=data)
    assert response.status_code != 200

    # Verify the size limit was effective
    sync_webserver.on_incoming.assert_not_called()


def test_save_error(sync_webserver, caplog):
    file_name = "testfile.txt"
    url = f"http://localhost:{sync_webserver.port}/{file_name}"
    data = b"data"

    sync_webserver.on_incoming = Mock(side_effect=IOError("Some error"))

    response = requests.put(url, data=data)
    assert response.status_code == 200
    assert "Some error" in caplog.text


def test_callback_error(sync_webserver, caplog):
    file_name = "testfile.txt"
    url = f"http://localhost:{sync_webserver.port}/{file_name}"
    data = b"data"

    mock_callback = Mock(side_effect=IOError())
    sync_webserver.on_incoming = mock_callback

    response = requests.put(url, data=data)
    assert response.status_code == 200
    assert "Error while receiving data" not in caplog.text
    assert "Error while invoking callback" in caplog.text
