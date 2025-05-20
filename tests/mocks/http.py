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
from typing import Any
from unittest.mock import Mock
from unittest.mock import patch

from local_console.servers.webserver import AsyncWebserver

MOCKED_WEBSERVER_PORT = 1234


class TestAsyncWebserver(AsyncWebserver):
    """
    Adds minimal syntactic sugar to support tests
    """

    async def receives_file(self, path: str, data: bytes) -> None:
        await self._recv_channel.send(
            (
                data,
                path,
            )
        )


@contextmanager
def mocked_http_server() -> Generator[AsyncWebserver, None, None]:
    with patch(
        "local_console.servers.webserver.GenericWebserver._setup_threads",
        mock_webserver_threads,
    ):
        http = TestAsyncWebserver(port=MOCKED_WEBSERVER_PORT)
        http.start()
        with (
            patch("local_console.servers.webserver.AsyncWebserver", http),
            patch("local_console.servers.webserver.SyncWebserver", http),
            patch("local_console.core.commands.deploy.SyncWebserver", http),
        ):
            yield http


def mock_webserver_threads(self: Any):
    mock_thread = Mock()
    mock_server = Mock()

    mock_server.server_port = MOCKED_WEBSERVER_PORT
    mock_thread.is_alive.return_value = True

    return mock_thread, mock_server
