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
from unittest.mock import Mock

import pytest
import trio
from local_console.core.camera.states.common import ConnectedCameraState
from local_console.core.camera.states.v2.deployment import ClearingAppCameraV2
from local_console.core.camera.states.v2.deployment import DeployingAppCameraV2
from local_console.core.camera.states.v2.ready import ReadyCameraV2
from local_console.core.commands.deploy import DeploymentSpec

from tests.mocks.method_extend import extend_method_async
from tests.mocks.mock_paho_mqtt import MockMqttAgent


@pytest.mark.trio
async def test_exit(nursery, monkeypatch, camera, mocked_agent_fixture: MockMqttAgent):
    await nursery.start(camera.setup)

    connected_exit = AsyncMock()
    extend_method_async(ConnectedCameraState, "exit", connected_exit, monkeypatch)

    state = ClearingAppCameraV2(
        camera._common_properties,
        DeploymentSpec.new_empty(),
        trio.Event(),
        Mock(),
        AsyncMock(),
    )
    await camera._transition_to_state(state)

    state = DeployingAppCameraV2(
        camera._common_properties,
        DeploymentSpec.new_empty(),
        trio.Event(),
        Mock(),
        AsyncMock(),
    )
    await camera._transition_to_state(state)
    connected_exit.assert_awaited()
    connected_exit.reset_mock()

    state = ReadyCameraV2(camera._common_properties)
    await camera._transition_to_state(state)
    connected_exit.assert_awaited()
