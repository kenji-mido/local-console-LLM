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
import trio
from local_console.core.camera.enums import ConnectionState
from local_console.core.camera.schemas import DeviceStateInformation
from local_console.core.deploy.deployment_manager import DeploymentManager
from local_console.core.device_services import DeviceServices
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes
from local_console.fastapi.routes.deploy_history.dto import DeviceDeployHistoryInfo


def test_deployment_manager_add_and_get_device():
    device_service = MagicMock()
    deployment_manager = DeploymentManager(device_service=device_service)
    deployment_manager.add_device_to_deployment("deploy_1", 1001)
    assert deployment_manager.get_devices_for_deployment("deploy_1") == [1001]


def test_deployment_manager_get_device_history():
    device_service = MagicMock()

    mock_device_dto = DeviceStateInformation(
        device_name="Device 1001",
        device_id="1001",
        internal_device_id="1001",
        description="Test Device",
        port=1001,
        modules=None,
        connection_state=ConnectionState.DISCONNECTED,
    )

    device_service.get_device.return_value = mock_device_dto
    deployment_manager = DeploymentManager(device_service=device_service)
    deployment_manager.add_device_to_deployment("deploy_2", 1001)
    device_history = deployment_manager.get_device_history_for_deployment("deploy_2")
    expected_device_history = [
        DeviceDeployHistoryInfo(device_id="1001", device_name="Device 1001")
    ]

    assert device_history == expected_device_history
    device_service.get_device.assert_called_once_with(1001)


def test_deployment_manager_device_not_found():
    deployment_manager = DeploymentManager(
        device_service=DeviceServices(
            MagicMock(spec=trio.Nursery),
            MagicMock(spec=trio.MemorySendChannel),
            MagicMock(spec=trio.lowlevel.TrioToken),
        )
    )

    deployment_manager.add_device_to_deployment("deploy_3", 3001)

    with pytest.raises(UserException) as e:
        deployment_manager.get_device_history_for_deployment("deploy_3")

    assert str(e.value) == "Device with id 3001 not found."
    assert e.value.code == ErrorCodes.EXTERNAL_DEVICE_NOT_FOUND
