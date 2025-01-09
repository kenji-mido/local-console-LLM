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
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from local_console.core.config import Config
from local_console.core.config import config_obj
from local_console.core.enums import config_paths


@pytest.fixture(autouse=True)
def reset_global_config():
    """
    Each test restores the default configuration
    """
    with tempfile.TemporaryDirectory() as tmpdirname:
        config_paths.home = Path(tmpdirname)
        config_obj._config = Config.get_default_config()
        yield


@pytest.fixture(autouse=True)
def skip_broker():
    with (
        patch(
            "local_console.commands.broker.spawn_broker",
        ),
        patch(
            "local_console.core.camera.mixin_mqtt.spawn_broker",
        ),
    ):
        yield


@pytest.fixture(autouse=True)
def skip_connection():
    with (
        patch(
            "local_console.clients.agent.AsyncClient",
        ),
    ):
        yield
