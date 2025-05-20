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
from contextlib import asynccontextmanager
from unittest.mock import MagicMock
from unittest.mock import Mock

import trio
from local_console.core.camera.machine import Camera
from local_console.core.camera.states.v1.common import ConnectedCameraStateV1
from local_console.core.device_services import DeviceServices
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.servers.webserver import AsyncWebserver
from local_console.servers.webserver import FileInbox

from tests.mocks.http import mocked_http_server
from tests.strategies.samplers.configs import DeviceConnectionSampler


def mocked_device_services(
    nursery: trio.Nursery = MagicMock(spec=trio.Nursery),
) -> DeviceServices:
    channel = MagicMock(spec=trio.MemorySendChannel)
    token = MagicMock(spec=trio.lowlevel.TrioToken)
    webserver = MagicMock(spec=AsyncWebserver)
    return DeviceServices(nursery, channel, webserver, token)


@asynccontextmanager
async def cs_init_context(
    mqtt_host: str = "localhost",
    mqtt_port: int = 1883,
    device_config: DeviceConfiguration | None = None,
) -> AsyncGenerator[Camera, None]:
    config = DeviceConnectionSampler().sample()

    config.mqtt.host = mqtt_host
    config.mqtt.port = mqtt_port

    with mocked_http_server() as webserver:
        camera = Camera(
            config,
            MagicMock(spec=trio.MemorySendChannel),
            webserver,
            MagicMock(spec=FileInbox),
            MagicMock(spec=trio.lowlevel.TrioToken),
            Mock(),
        )

        camera._state = ConnectedCameraStateV1(camera._common_properties)
        if device_config:
            camera._state._refresh_from_report(device_config)

        yield camera
