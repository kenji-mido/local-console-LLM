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
from pathlib import Path
from unittest.mock import patch

import pytest
from local_console.core.config import Config
from local_console.core.config import ConfigPersistency
from local_console.core.config import OnDisk
from local_console.core.schemas.schemas import GlobalConfiguration

# See https://docs.pytest.org/en/stable/how-to/fixtures.html#using-fixtures-from-other-projects
pytest_plugins = (
    "tests.fixtures.agent",
    "tests.fixtures.camera",
    "tests.fixtures.configs",
    "tests.fixtures.debugging",
    "tests.fixtures.devices",
    "tests.fixtures.drawer",
    "tests.fixtures.fastapi",
    "tests.fixtures.firmware",
)


class InMemory(ConfigPersistency):
    """
    This class object makes its read/save_config() methods do no I/O operations,
    using instead an in-memory GlobalConfiguration instance.
    """

    def __init__(self) -> None:
        self.persistent_conf: GlobalConfiguration | None = None
        self.read_count = 0
        self.write_count = 0

    def save_config(self, conf: GlobalConfiguration) -> None:
        self.write_count += 1
        self.persistent_conf = conf.model_copy(deep=True)

    def read_config(self) -> GlobalConfiguration:
        assert self.persistent_conf
        self.read_count += 1
        return self.persistent_conf.model_copy(deep=True)


@pytest.fixture(autouse=True)
def global_config_without_io(tmp_path: Path) -> Generator[None, None, None]:
    """
    The singleton's persistency class is replaced with an I/O-less variant
    """
    Config().reset()
    with (
        patch.object(Config, "persistency_class", InMemory),
        patch(
            "local_console.core.schemas.utils.get_default_files_dir",
            return_value=tmp_path,
        ),
    ):
        if type(Config()._persistency_obj) is OnDisk:
            Config()._persistency_obj = InMemory()

        yield

    # Maybe this reset to default is unnecessary
    Config.persistency_class = OnDisk


@pytest.fixture(autouse=True)
def skip_broker() -> Generator[None, None, None]:
    with (
        patch(
            "local_console.commands.broker.spawn_broker",
        ),
        patch(
            "local_console.core.camera.states.base.spawn_broker",
        ),
    ):
        yield


@pytest.fixture(autouse=True)
def skip_connection() -> Generator[None, None, None]:
    with (
        patch(
            "local_console.clients.agent.AsyncClient",
        ),
    ):
        yield
