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
from local_console.core.camera.machine import Camera
from local_console.core.camera.schemas import DeviceStateInformation
from local_console.core.deploy.deployment_manager import DeploymentManager
from local_console.core.device_services import DeviceServices
from local_console.core.schemas.schemas import DeviceType
from local_console.fastapi.routes.deploy_history.dto import DeviceDeployHistoryInfo
from local_console.servers.webserver import AsyncWebserver
from local_console.servers.webserver import FileInbox

from tests.mocks.config import set_configuration
from tests.strategies.samplers.configs import GlobalConfigurationSampler


def test_deployment_manager_add_and_get_device_history():
    device_service = MagicMock()

    mock_device_dto = DeviceStateInformation(
        device_name="Device 1001",
        device_type=DeviceType.T3P_AIH,
        device_id="1001",
        internal_device_id="1001",
        description="Test Device",
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


@pytest.mark.trio
async def test_deployment_manager_if_device_has_been_removed_from_service():

    simple_gconf = GlobalConfigurationSampler(num_of_devices=2).sample()
    set_configuration(simple_gconf)

    device_conn_conf = simple_gconf.devices[0]
    device_name = device_conn_conf.name
    device_id = device_conn_conf.mqtt.port
    assert device_id != 3001
    set_configuration(simple_gconf)

    device_service = DeviceServices(
        MagicMock(spec=trio.Nursery),
        MagicMock(spec=trio.MemorySendChannel),
        MagicMock(spec=AsyncWebserver),
        MagicMock(spec=trio.lowlevel.TrioToken),
    )

    for device_conn in simple_gconf.devices:
        camera = Camera(
            device_conn,
            MagicMock(spec=trio.MemorySendChannel),
            MagicMock(spec=AsyncWebserver),
            MagicMock(spec=FileInbox),
            MagicMock(spec=trio.lowlevel.TrioToken),
            lambda *args: None,
        )
        device_service.set_camera(device_conn.id, camera)

    deployment_manager = DeploymentManager(device_service=device_service)

    deployment_manager.add_device_to_deployment("deploy_2", device_id)
    device_service.remove_device(device_id)
    expected_device_history = [
        DeviceDeployHistoryInfo(device_id=str(device_id), device_name=device_name)
    ]
    device_history = deployment_manager.get_device_history_for_deployment("deploy_2")

    assert device_history == expected_device_history
