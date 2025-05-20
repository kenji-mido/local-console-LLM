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
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest
import trio
from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.camera.enums import OTAUpdateStatus
from local_console.core.camera.machine import Camera
from local_console.core.camera.states.base import StateWithProperties
from local_console.core.camera.states.v1.ota_sensor import ClearingSensorModelCameraV1
from local_console.core.camera.states.v1.ota_sensor import UpdateSensorModelCameraV1
from local_console.core.schemas.edge_cloud_if_v1 import DnnDelete
from local_console.core.schemas.edge_cloud_if_v1 import DnnDeleteBody
from local_console.core.schemas.edge_cloud_if_v1 import DnnOta
from local_console.core.schemas.edge_cloud_if_v1 import DnnOtaBody
from local_console.core.schemas.schemas import GlobalConfiguration
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.servers.webserver import SyncWebserver

from tests.mocks.http import MOCKED_WEBSERVER_PORT
from tests.mocks.mock_paho_mqtt import MockMqttAgent
from tests.strategies.samplers.mqtt_message import MockMQTTMessage


@pytest.fixture(params=[OTAUpdateStatus.DONE, OTAUpdateStatus.FAILED])
def update_status(request):
    return request.param


@pytest.fixture(params=["000001", "123456"])
def network_id(request):
    return request.param


class WaitingState(StateWithProperties):
    """
    Use to detect the transition to this state.
    E.g.,
        await WaitingState().event.wait()
    """

    def __init__(self, *args: Any):
        self.event = trio.Event()

    async def enter(self, nursery: trio.Nursery) -> None:
        self.event.set()


@pytest.fixture
async def v1_camera(
    camera, mocked_agent_fixture, single_device_config, nursery
) -> AsyncGenerator[[Camera, MockMqttAgent, trio.Nursery], None]:
    """
    Set starting state up for a camera instance with mocked messaging
    """
    with (patch("local_console.core.camera.states.base.spawn_broker"),):
        await nursery.start(camera.setup)
        yield camera, mocked_agent_fixture, single_device_config, nursery


@pytest.mark.trio
async def test_clearing_sensor_model_camera_v1(
    v1_camera: tuple[Camera, MockMqttAgent, GlobalConfiguration, trio.Nursery],
    network_id,
    tmp_path,
):
    camera, mqtt_client, g_config, nursery = v1_camera

    package_file = tmp_path / "dummy.bin"
    package_file.write_bytes(b"some (not) random bytes")

    wait_class = WaitingState()

    with (
        patch(
            "local_console.core.camera.states.v1.ota_sensor.publish_configure"
        ) as mock_publish_configure,
        patch(
            "local_console.core.camera.states.v1.ota_sensor.get_network_id",
            return_value=network_id,
        ) as mock_get_network_id,
        patch(
            "local_console.core.camera.states.v1.ota_sensor.UpdateSensorModelCameraV1",
            return_value=wait_class,
        ),
    ):
        await camera._transition_to_state(
            ClearingSensorModelCameraV1(
                camera._common_properties, package_file, trio.Event(), AsyncMock()
            )
        )

        mqtt_client.receives(MockMQTTMessage.config_status(update_status="Updating"))
        mqtt_client.receives(
            MockMQTTMessage.config_status(dnn_model_version=[], update_status="Done")
        )

        # Wait for ClearingSensorModelCameraV1 to transition to UpdateSensorModelCameraV1
        await wait_class.event.wait()

        # Network ID is extracted from package file
        mock_get_network_id.assert_called_once_with(package_file)

        # Undeploy NN configuration
        mock_publish_configure.assert_awaited_once_with(
            mqtt_client.agent,
            OnWireProtocol.EVP1,
            "backdoor-EA_Main",
            "placeholder",
            DnnDelete(
                OTA=DnnDeleteBody(UpdateModule="DnnModel", DeleteNetworkID=network_id)
            ).model_dump_json(),
        )


@pytest.mark.trio
async def test_update_sensor_model_camera_v1(
    v1_camera: tuple[Camera, MockMqttAgent, GlobalConfiguration, trio.Nursery],
    network_id,
    tmp_path,
):
    camera, mqtt_client, g_config, nursery = v1_camera
    dev_conf = g_config.devices[0]

    package_file = tmp_path / "dummy.bin"
    package_file.write_bytes(b"some (not) random bytes")

    event = trio.Event()
    with (
        patch(
            "local_console.core.camera.states.v1.ota_sensor.publish_configure"
        ) as mock_publish_configure,
        patch(
            "local_console.core.camera.states.v1.ota_sensor.get_network_id",
            return_value=network_id,
        ) as mock_get_network_id,
        patch(
            "local_console.core.commands.ota_deploy.get_package_version",
            return_value="XXXXXX" + network_id,
        ),
        patch(
            "local_console.core.commands.ota_deploy.get_package_hash",
            return_value="abc",
        ),
        patch.object(
            UpdateSensorModelCameraV1,
            "_transition_out",
            new_callable=lambda: event.set(),
        ),
    ):
        await camera._transition_to_state(
            UpdateSensorModelCameraV1(
                camera._common_properties, package_file, trio.Event(), AsyncMock()
            )
        )

        mqtt_client.receives(
            MockMQTTMessage.config_status(
                dnn_model_version=[], update_status="Updating"
            )
        )
        mqtt_client.receives(
            MockMQTTMessage.config_status(
                dnn_model_version=[network_id], update_status="Done"
            )
        )

        # Wait for UpdateSensorModelCameraV1 to transition out
        await event.wait()

        # Network ID is extracted from package file
        mock_get_network_id.assert_called_once_with(package_file)

        url_path = SyncWebserver.url_path_for(package_file)
        mock_publish_configure.assert_awaited_once_with(
            mqtt_client.agent,
            OnWireProtocol.EVP1,
            "backdoor-EA_Main",
            "placeholder",
            DnnOta(
                OTA=DnnOtaBody(
                    UpdateModule=OTAUpdateModule.DNNMODEL,
                    DesiredVersion="XXXXXX" + network_id,
                    PackageUri=f"http://{dev_conf.mqtt.host}:{MOCKED_WEBSERVER_PORT}{url_path}",
                    HashValue="abc",
                )
            ).model_dump_json(),
        )
