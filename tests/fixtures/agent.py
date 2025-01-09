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
from contextlib import asynccontextmanager
from contextlib import contextmanager
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
import trio
from local_console.core.camera.state import CameraState

from tests.fixtures.camera import cs_init_context
from tests.mocks.files import mock_files_manager
from tests.mocks.files import MockedFileManager
from tests.mocks.http import mocked_http_server
from tests.mocks.http import MockedHttpServer
from tests.mocks.mock_paho_mqtt import MockMqttAgent
from tests.strategies.samplers.device_config import DeviceConfigurationSampler


class MockedIOs:
    def __init__(
        self,
        mqtt: MockMqttAgent,
        http: MockedHttpServer,
        files: MockedFileManager,
        state: CameraState,
    ):
        self.mqtt = mqtt
        self.http = http
        self.files = files
        self.state = state


@contextmanager
def mocked_agent() -> Generator[MockMqttAgent, None, None]:
    agent = MagicMock()
    with (
        patch("local_console.core.camera.mixin_mqtt.TimeoutBehavior"),
        patch("local_console.core.camera.firmware.Agent", agent),
        patch("local_console.core.camera.mixin_mqtt.Agent", agent),
        patch("local_console.core.camera.ai_model.Agent", agent),
        patch("local_console.core.camera.mixin_mqtt.spawn_broker"),
        patch("local_console.core.camera.state.CameraState._undeploy_apps"),
        patch(
            "local_console.core.camera.mixin_streaming.StreamingMixin.blobs_webserver_task"
        ),
    ):
        yield MockMqttAgent(agent)


@asynccontextmanager
async def running_servers() -> AsyncGenerator[MockedIOs, None]:
    with (
        mocked_agent() as agent,
        mocked_http_server() as http,
        mock_files_manager() as file_manager,
    ):
        async with (
            cs_init_context(
                device_config=DeviceConfigurationSampler().sample()
            ) as state,
            trio.open_nursery() as nursery,
        ):
            agent.wait_for_messages = True
            state._init_bindings_mqtt()
            state._nursery = nursery
            with trio.move_on_after(120):
                nursery.start_soon(state.mqtt_setup)
                for _ in range(40):
                    await trio.sleep(0.005)
                    if state.mqtt_client:
                        break
                yield MockedIOs(mqtt=agent, http=http, files=file_manager, state=state)
            agent.wait_for_messages = False


@pytest.fixture()
def mocked_agent_fixture():
    """
    This construction is necessary because hypothesis does not
    support using custom pytest fixtures from cases that it
    manages (i.e. cases decorated with @given).
    """
    with mocked_agent() as agent:
        yield agent
