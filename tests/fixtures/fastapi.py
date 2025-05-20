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
from collections.abc import Generator
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
import trio
from fastapi.testclient import TestClient
from httpx import ASGITransport
from httpx import AsyncClient
from httpx_ws.transport import ASGIWebSocketTransport
from local_console.core.camera.machine import Camera
from local_console.core.deploy.tasks.task_executors import TrioBackgroundTasks
from local_console.core.deploy_config import DeployConfigManager
from local_console.core.device_services import DeviceServices
from local_console.core.edge_apps import EdgeAppsManager
from local_console.core.files.files import FilesManager
from local_console.core.firmwares import FirmwareManager
from local_console.core.models import ModelManager
from local_console.core.schemas.schemas import GlobalConfiguration
from local_console.fastapi.main import generate_server
from local_console.fastapi.main import lifespan

from tests.fixtures.agent import mocked_agent
from tests.mocks.mock_paho_mqtt import MockMqttAgent


@pytest.fixture
def fa_client() -> Generator[TestClient, None, None]:
    app = generate_server()
    app.state.device_service = DeviceServices(
        nursery=MagicMock(),
        channel=MagicMock(),
        webserver=MagicMock(),
        token=MagicMock(),
    )
    file_manager = MagicMock(spec=FilesManager)
    app.state.file_manager = file_manager
    app.state.model_manager = ModelManager(file_manager)
    app.state.firmware_manager = FirmwareManager(file_manager)
    app.state.model_manager = ModelManager(file_manager)
    app.state.edge_apps_manager = EdgeAppsManager(file_manager)
    app.state.deploy_config_manager = DeployConfigManager(
        app.state.model_manager,
        app.state.edge_apps_manager,
        app.state.firmware_manager,
    )
    app.state.deploy_background_task = TrioBackgroundTasks()
    yield TestClient(app=app)


@pytest.fixture
async def fa_client_with_agent(
    mocked_agent_fixture: MockMqttAgent,
    single_device_config: GlobalConfiguration,
) -> AsyncGenerator[AsyncClient, None, None]:
    agent = mocked_agent_fixture
    app = generate_server()
    async with lifespan(app):
        for _ in range(20):
            if agent.has_been_called():
                break
            else:
                await trio.sleep(0.05)
        if not agent.has_been_called():
            raise AssertionError("Could not start mqtt server")
        yield AsyncClient(transport=ASGITransport(app), base_url="http://local.console")


@pytest.fixture
async def fa_client_async(
    nursery,
    single_device_config: GlobalConfiguration,
) -> AsyncGenerator[AsyncClient, None]:
    app = generate_server()
    app.state.device_service = DeviceServices(
        nursery=nursery, channel=MagicMock(), webserver=MagicMock(), token=MagicMock()
    )
    yield AsyncClient(transport=ASGITransport(app), base_url="http://local.console")


@pytest.fixture
async def fa_client_full_init(
    single_device_config: GlobalConfiguration,
) -> AsyncGenerator[tuple[AsyncClient, Camera], None]:
    dev_id = single_device_config.devices[0].mqtt.port
    with (
        patch("local_console.fastapi.main.running_background_task"),
        patch("local_console.fastapi.main.stop_background_task"),
        mocked_agent() as agent,
    ):
        app = generate_server()
        async with lifespan(app):
            camera = app.state.device_service.get_camera(dev_id)
            client = AsyncClient(
                transport=ASGIWebSocketTransport(app), base_url="http://test"
            )
            yield client, camera

        agent.stop_receiving_messages()
