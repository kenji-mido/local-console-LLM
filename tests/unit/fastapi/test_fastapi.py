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
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from local_console.core.device_services import DeviceServices

from tests.fixtures.agent import mocked_agent_fixture
from tests.fixtures.fastapi import fa_client_with_agent
from tests.mocks.mock_paho_mqtt import MockMqttAgent
from tests.strategies.samplers.configs import DeviceConnectionSampler


@pytest.mark.trio
async def test_start_mqtt_with_fast_api(
    fa_client_with_agent: AsyncClient,
    mocked_agent_fixture: MockMqttAgent,
) -> None:
    agent = mocked_agent_fixture

    assert fa_client_with_agent
    agent.has_been_initialized_on_port(DeviceServices.DEFAULT_DEVICE_PORT)


@pytest.mark.trio
async def test_cleanup() -> None:

    from local_console.fastapi.main import lifespan

    app = FastAPI(title="Local console Web UI", lifespan=lifespan)
    with (
        patch("local_console.fastapi.main.config_obj") as mock_config,
        patch("local_console.core.camera.state.CameraState.shutdown") as mock_shutdown,
    ):
        num_of_devices = 5
        mock_config.get_device_configs.return_value = (
            DeviceConnectionSampler().list_of_samples(num_of_devices)
        )

        async with lifespan(app):
            # The 'pass' below represents the process reaching the
            # moment when it should exit (either due to an error or
            # because it received SIGTERM/SIGINT). That initiates
            # the shutdown phase of the lifespan.
            pass

        mock_shutdown.assert_called()
        assert mock_shutdown.call_count == num_of_devices
