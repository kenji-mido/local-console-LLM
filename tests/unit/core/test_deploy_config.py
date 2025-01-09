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
from unittest.mock import MagicMock

import pytest
from local_console.core.deploy_config import DeployConfig
from local_console.core.deploy_config import DeployConfigManager
from local_console.core.files.exceptions import FileNotFound

from tests.strategies.samplers.files import DeployConfigInSampler
from tests.strategies.samplers.files import EdgeAppSampler
from tests.strategies.samplers.files import FirmwareSampler
from tests.strategies.samplers.files import ModelSampler


def test_deploy_config_manager():
    firmware_m = MagicMock()
    firmware = FirmwareSampler().sample()
    app_m = MagicMock()
    app = EdgeAppSampler().sample()
    model_m = MagicMock()
    model = ModelSampler().sample()
    config_manager = DeployConfigManager(
        model_manager=model_m, edge_app_manager=app_m, fw_manager=firmware_m
    )
    firmware_m.get_by_id.return_value = firmware
    app_m.get_by_id.return_value = app
    model_m.get_by_id.return_value = model
    config_in = DeployConfigInSampler().sample()

    assert config_manager.get_by_id(config_in.config_id) is None

    config_manager.register(config_in)
    firmware_m.get_by_id.assert_called_once_with(config_in.fw_ids[0])
    app_m.get_by_id.assert_called_with(config_in.edge_apps[0].edge_app_id)
    model_m.get_by_id.assert_called_once_with(config_in.model_ids[0])
    firmware_m.reset_mock()
    app_m.reset_mock()
    model_m.reset_mock()
    detailed: DeployConfig | None = config_manager.get_by_id(config_in.config_id)
    assert detailed is not None
    assert detailed.config_id == config_in.config_id
    assert detailed.firmwares == [firmware]
    assert detailed.edge_apps == [app]
    assert detailed.models == [model]
    firmware_m.get_by_id.assert_called_once_with(config_in.fw_ids[0])
    app_m.get_by_id.assert_called_once_with(config_in.edge_apps[0].edge_app_id)
    model_m.get_by_id.assert_called_once_with(config_in.model_ids[0])


def test_check_deploy_config_edge_app_not_found():
    firmware_m = MagicMock()
    firmware = FirmwareSampler().sample()
    app_m = MagicMock()
    app = EdgeAppSampler().sample()
    model_m = MagicMock()
    model = ModelSampler().sample()
    config_manager = DeployConfigManager(
        model_manager=model_m, edge_app_manager=app_m, fw_manager=firmware_m
    )
    firmware_m.get_by_id.return_value = firmware
    app_m.get_by_id.return_value = app
    model_m.get_by_id.return_value = model
    config_in = DeployConfigInSampler().sample()
    config_manager.register(config_in)
    firmware_m.reset_mock()
    app_m.reset_mock()
    model_m.reset_mock()

    app_m.get_by_id.return_value = None
    with pytest.raises(FileNotFound):
        config_manager.get_by_id(config_in.config_id)
    app_m.get_by_id.assert_called_once_with(config_in.edge_apps[0].edge_app_id)


def test_check_deploy_config_model_not_found():
    firmware_m = MagicMock()
    firmware = FirmwareSampler().sample()
    app_m = MagicMock()
    app = EdgeAppSampler().sample()
    model_m = MagicMock()
    model = ModelSampler().sample()
    config_manager = DeployConfigManager(
        model_manager=model_m, edge_app_manager=app_m, fw_manager=firmware_m
    )
    firmware_m.get_by_id.return_value = firmware
    app_m.get_by_id.return_value = app
    model_m.get_by_id.return_value = model
    config_in = DeployConfigInSampler().sample()
    config_manager.register(config_in)
    firmware_m.reset_mock()
    app_m.reset_mock()
    model_m.reset_mock()

    model_m.get_by_id.return_value = None
    with pytest.raises(FileNotFound):
        config_manager.get_by_id(config_in.config_id)
    model_m.get_by_id.assert_called_once_with(config_in.model_ids[0])


def test_check_deploy_config_fw_not_found():
    firmware_m = MagicMock()
    firmware = FirmwareSampler().sample()
    app_m = MagicMock()
    app = EdgeAppSampler().sample()
    model_m = MagicMock()
    model = ModelSampler().sample()
    config_manager = DeployConfigManager(
        model_manager=model_m, edge_app_manager=app_m, fw_manager=firmware_m
    )
    firmware_m.get_by_id.return_value = firmware
    app_m.get_by_id.return_value = app
    model_m.get_by_id.return_value = model
    config_in = DeployConfigInSampler().sample()
    config_manager.register(config_in)
    firmware_m.reset_mock()
    app_m.reset_mock()
    model_m.reset_mock()

    firmware_m.get_by_id.return_value = None
    with pytest.raises(FileNotFound):
        config_manager.get_by_id(config_in.config_id)
    firmware_m.get_by_id.assert_called_once_with(config_in.fw_ids[0])
