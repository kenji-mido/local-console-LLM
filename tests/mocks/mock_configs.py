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
from unittest.mock import MagicMock
from unittest.mock import patch

from local_console.core.config import Config
from local_console.core.device_services import DeviceServices
from local_console.core.schemas.schemas import GlobalConfiguration
from typing_extensions import (
    Self,
)  # Added in typing in Python 3.11: https://docs.python.org/3/library/typing.html#typing.Self


class ConfigMocker(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(spec=Config, *args, **kwargs)

    @staticmethod
    @contextmanager
    def mock_configuration(
        config: GlobalConfiguration, device_services: DeviceServices | None = None
    ) -> Generator[Self, None, None]:
        file_config = Config()
        file_config._config = config
        mocked = ConfigMocker(wraps=file_config)
        if device_services:
            for device in config.devices:
                device_services.add_device_to_internals(device)
        with patch.object(mocked, "config", config):
            yield mocked


@contextmanager
def config_without_io(
    config: GlobalConfiguration,
) -> Generator[Config, None, None]:
    config_during_test = Config()
    config_during_test._config = config

    with (
        patch.object(config_during_test, "read_config"),
        patch.object(config_during_test, "save_config"),
        patch("local_console.core.device_services.config_obj", config_during_test),
        patch("local_console.core.camera.qr.qr.config_obj", config_during_test),
        patch("local_console.core.camera.state.CameraState._init_bindings"),
    ):
        yield config_during_test
