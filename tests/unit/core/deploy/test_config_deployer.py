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
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest
from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.camera.state import CameraState
from local_console.core.deploy.config_deployer import ConfigDeployer
from local_console.core.deploy.tasks.app_task import AppTask
from local_console.core.deploy.tasks.config_task import ConfigTask
from local_console.core.deploy.tasks.firmware_task import FirmwareTask
from local_console.core.deploy.tasks.model_task import ModelTask
from local_console.core.deploy.tasks.task_executors import TaskExecutor
from local_console.core.deploy_config import DeployConfigManager
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes
from local_console.core.schemas.schemas import DeploymentConfig

from tests.mocks.devices import mocked_device_services
from tests.strategies.samplers.device_config import DeviceConfigurationSampler
from tests.strategies.samplers.files import DeployConfigSampler


def _deployer() -> ConfigDeployer:
    devices = mocked_device_services()
    configs = MagicMock(spec=DeployConfigManager)
    tasks = AsyncMock(spec=TaskExecutor)
    params = DeploymentConfig()
    return ConfigDeployer(devices, configs, tasks, params)


@pytest.mark.trio
async def test_deploy() -> None:
    device = CameraState(MagicMock(), MagicMock())
    config = DeployConfigSampler(num_apps=1, num_models=1).sample()
    deployer = _deployer()
    device_id = 1

    deployer.devices.states[device_id] = device
    deployer.configs.get_by_id.return_value = config

    await deployer.deploy(device_id, config.config_id)

    deployer.configs.get_by_id.assert_called_once_with(config.config_id)

    deploy_task = deployer.tasks.add_task.await_args[0][0]
    assert isinstance(deploy_task, ConfigTask)
    assert deploy_task._camera_state == device
    assert len(deploy_task._tasks) == 3
    assert isinstance(deploy_task._tasks[0], FirmwareTask)
    assert deploy_task._tasks[0].firmware == config.firmwares[0]
    assert deploy_task._tasks[0].camera_state == device
    assert isinstance(deploy_task._tasks[1], AppTask)
    assert deploy_task._tasks[1]._app == config.edge_apps[0]
    assert deploy_task._tasks[1]._camera_state == device
    assert isinstance(deploy_task._tasks[2], ModelTask)
    assert deploy_task._tasks[2].model == config.models[0]
    assert deploy_task._tasks[2].camera_state == device


@pytest.mark.trio
async def test_error_on_device_not_found() -> None:
    config = DeployConfigSampler(num_apps=1, num_models=1).sample()
    deployer = _deployer()
    device_id = 1

    with pytest.raises(FileNotFoundError) as error:
        await deployer.deploy(device_id, config.config_id)

    assert str(error.value) == f"Device with id {device_id} not found."


@pytest.mark.trio
async def test_error_on_config_not_found() -> None:
    device = MagicMock(spec=CameraState)
    config = DeployConfigSampler(num_apps=1, num_models=1).sample()
    deployer = _deployer()
    device_id = 1

    deployer.devices.states[device_id] = device
    deployer.configs.get_by_id.return_value = None
    with pytest.raises(FileNotFoundError) as error:
        await deployer.deploy(device_id, config.config_id)

    assert str(error.value) == f"Config with id {config.config_id} not found."


@pytest.mark.trio
async def test_sensor_firmware_at_same_version() -> None:
    device = CameraState(MagicMock(), MagicMock())
    device.device_config.value = DeviceConfigurationSampler().sample()
    device.mqtt_port = device.device_config.value.Network.ProxyPort
    device_id = device.mqtt_port
    config = DeployConfigSampler(num_apps=1, num_models=1).sample()

    config.firmwares[0].info.firmware_type = OTAUpdateModule.SENSORFW
    config.firmwares[0].info.version = (
        device.device_config.value.Version.SensorFwVersion
    )
    deployer = _deployer()
    deployer.devices.states[device_id] = device
    deployer.configs.get_by_id.return_value = config

    with pytest.raises(UserException) as error:
        await deployer.deploy(device_id, config.config_id)

    assert str(error.value) == "Already same Firmware version is available"
    assert error.value.code == ErrorCodes.EXTERNAL_FIRMWARE_SAME_VERSION


@pytest.mark.trio
async def test_app_firmware_at_same_version() -> None:
    device = CameraState(MagicMock(), MagicMock())
    device.device_config.value = DeviceConfigurationSampler().sample()
    device.mqtt_port = device.device_config.value.Network.ProxyPort
    device_id = device.mqtt_port
    config = DeployConfigSampler(num_apps=1, num_models=1).sample()

    config.firmwares[0].info.firmware_type = OTAUpdateModule.APFW
    config.firmwares[0].info.version = device.device_config.value.Version.ApFwVersion
    deployer = _deployer()
    deployer.devices.states[device_id] = device
    deployer.configs.get_by_id.return_value = config

    with pytest.raises(UserException) as error:
        await deployer.deploy(device_id, config.config_id)

    assert str(error.value) == "Already same Firmware version is available"
    assert error.value.code == ErrorCodes.EXTERNAL_FIRMWARE_SAME_VERSION
