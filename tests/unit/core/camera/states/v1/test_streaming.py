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
from unittest.mock import patch

import pytest
import trio
from local_console.core.camera.machine import Camera
from local_console.core.camera.states.common import DisconnectedCamera
from local_console.core.camera.states.v1.streaming import StreamingCameraV1
from local_console.core.schemas.edge_cloud_if_v1 import StartUploadInferenceData
from local_console.core.schemas.schemas import DeviceConnection
from local_console.servers.webserver import AsyncWebserver
from local_console.servers.webserver import FileInbox

from tests.mocks.http import mocked_http_server
from tests.mocks.http import MOCKED_WEBSERVER_PORT


@pytest.fixture
async def mocked_webserver():
    with mocked_http_server() as server:
        yield server


@pytest.mark.trio
async def test_streaming_enter(single_device_config, mocked_webserver, nursery):
    config: DeviceConnection = single_device_config.devices[0]

    file_inbox = FileInbox(mocked_webserver)

    camera = Camera(
        config,
        MagicMock(spec=trio.MemorySendChannel),
        mocked_webserver,
        file_inbox,
        MagicMock(spec=trio.lowlevel.TrioToken),
        lambda x: x,
    )
    await nursery.start(camera.setup)

    url = f"http://{config.mqtt.host}:{MOCKED_WEBSERVER_PORT}/{config.id}"
    payload = {
        "CropHOffset": 1,
        "CropVOffset": 1,
        "CropHSize": 1,
        "CropVSize": 1,
    }
    body = StartUploadInferenceData(
        StorageName=url,
        StorageSubDirectoryPath="images",
        StorageNameIR=url,
        StorageSubDirectoryPathIR="inferences",
        **payload,
    )

    state = StreamingCameraV1(camera._common_properties, payload, {})

    with (
        patch(
            "local_console.core.camera.states.v1.common.run_rpc_with_response",
            AsyncMock(),
        ) as mock_run_rpc_with_response,
    ):
        await camera._transition_to_state(state)

        mock_run_rpc_with_response.assert_awaited_once_with(
            state._mqtt._mqtt_port,
            "backdoor-EA_Main",
            "StartUploadInferenceData",
            body.model_dump(),
        )


@pytest.mark.trio
async def test_streaming_exit(single_device_config, nursery):
    config: DeviceConnection = single_device_config.devices[0]
    mock_file_inbox = MagicMock(spec=FileInbox)

    camera = Camera(
        config,
        MagicMock(spec=trio.MemorySendChannel),
        MagicMock(spec=AsyncWebserver),
        mock_file_inbox,
        MagicMock(spec=trio.lowlevel.TrioToken),
        lambda x: x,
    )
    await nursery.start(camera.setup)

    payload = {
        "CropHOffset": 1,
        "CropVOffset": 1,
        "CropHSize": 1,
        "CropVSize": 1,
    }
    state = StreamingCameraV1(camera._common_properties, payload, {})
    camera._state = state

    with (
        patch(
            "local_console.core.camera.states.v1.common.run_rpc_with_response",
            AsyncMock(),
        ) as mock_run_rpc_with_response,
    ):
        mock_run_rpc_with_response.reset_mock()

        # Exit streaming
        await camera._transition_to_state(DisconnectedCamera(camera._common_properties))

        mock_run_rpc_with_response.assert_awaited_once_with(
            state._mqtt._mqtt_port, "backdoor-EA_Main", "StopUploadInferenceData", {}
        )
        mock_file_inbox.reset_file_incoming_callable.assert_called_once_with(config.id)
