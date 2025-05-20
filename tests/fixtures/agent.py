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
from local_console.core.camera.machine import Camera

from tests.mocks.config import set_configuration
from tests.mocks.devices import cs_init_context
from tests.mocks.files import mock_files_manager
from tests.mocks.files import MockedFileManager
from tests.mocks.http import AsyncWebserver
from tests.mocks.http import mocked_http_server
from tests.mocks.mock_paho_mqtt import MockMqttAgent
from tests.strategies.samplers.configs import GlobalConfigurationSampler
from tests.strategies.samplers.device_config import DeviceConfigurationSampler


class MockedIOs:
    def __init__(
        self,
        mqtt: MockMqttAgent,
        http: AsyncWebserver,
        files: MockedFileManager,
        camera: Camera,
    ):
        self.mqtt = mqtt
        self.http = http
        self.files = files
        self.camera = camera


@contextmanager
def mocked_agent() -> Generator[MockMqttAgent, None, None]:

    agent_class_mock = MagicMock()
    mocked_agent = MockMqttAgent(agent_class_mock)

    with (
        # From `git grep "TimeoutBehavior"`
        patch("local_console.core.camera.states.common.TimeoutBehavior"),
        patch("local_console.core.camera.states.v2.ready.TimeoutBehavior"),
        # From `git grep "Agent("`
        patch("local_console.commands.config.Agent", agent_class_mock),
        patch("local_console.commands.get.Agent", agent_class_mock),
        patch("local_console.commands.logs.Agent", agent_class_mock),
        patch("local_console.core.camera.states.base.Agent", agent_class_mock),
        patch("local_console.core.camera.states.v1.ota_sensor.Agent", agent_class_mock),
        patch("local_console.core.camera.states.v1.ota_sys.Agent", agent_class_mock),
        patch("local_console.core.camera.states.v1.rpc.Agent", agent_class_mock),
        patch("local_console.core.commands.rpc_with_response.Agent", agent_class_mock),
    ):
        yield mocked_agent


@asynccontextmanager
async def single_device_cxmg() -> AsyncGenerator[
    [
        Camera,
        MockMqttAgent,
    ],
    None,
]:
    simple_gconf = GlobalConfigurationSampler(num_of_devices=1).sample()
    device_conn_conf = simple_gconf.devices[0]
    set_configuration(simple_gconf)
    with mocked_agent() as agent:
        async with (
            trio.open_nursery() as nursery,
            cs_init_context(
                mqtt_host=device_conn_conf.mqtt.host,
                mqtt_port=device_conn_conf.mqtt.port,
                device_config=DeviceConfigurationSampler().sample(),
            ) as state,
        ):
            state._init_bindings_mqtt()
            state._nursery = nursery
            await nursery.start(state.mqtt_setup)
            yield (
                state,
                agent,
            )
            agent.stop_receiving_messages()


@pytest.fixture
async def single_device_ctx() -> AsyncGenerator[
    [
        Camera,
        MockMqttAgent,
    ],
    None,
]:
    async with single_device_cxmg() as objects:
        yield objects


@asynccontextmanager
async def running_servers() -> AsyncGenerator[MockedIOs, None]:
    with (
        mocked_http_server() as http,
        mock_files_manager() as file_manager,
    ):
        async with single_device_cxmg() as (
            camera,
            agent,
        ):
            yield MockedIOs(
                mqtt=agent,
                http=http,
                files=file_manager,
                camera=camera,
            )


@pytest.fixture()
def mocked_agent_fixture():
    """
    This construction is necessary because hypothesis does not
    support using custom pytest fixtures from cases that it
    manages (i.e. cases decorated with @given).
    """
    with (mocked_agent() as agent,):
        yield agent
        agent.stop_receiving_messages()
