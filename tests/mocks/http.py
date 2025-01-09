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
from unittest.mock import MagicMock
from unittest.mock import patch


class MockedHttpServer(MagicMock):
    def __init__(self, *args: Any, **kw: Any) -> None:
        super().__init__(*args, **kw)

    def initialized_dir(self) -> Path:
        if self.call_count <= 0:
            return None
        return self.call_args.args[0]

    def external_set_dir(self) -> Path:
        if self.return_value.set_directory.call_count <= 0:
            return None
        return self.return_value.set_directory.call_args.args[0]


@contextmanager
def mocked_http_server() -> Generator[MockedHttpServer, None, None]:
    http = MockedHttpServer()
    with (
        patch("local_console.core.camera.firmware.AsyncWebserver", http),
        patch("local_console.servers.webserver.SyncWebserver", http),
        patch("local_console.core.camera.ai_model.AsyncWebserver", http),
        patch("local_console.core.commands.deploy.SyncWebserver", http),
    ):
        yield http
