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
import json
from base64 import b64encode
from unittest.mock import ANY
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
import trio
from local_console.core.camera.enums import MQTTTopics
from local_console.core.camera.machine import Camera
from local_console.core.camera.states.v2.ready import ReadyCameraV2
from local_console.core.camera.v2.components.direct_get_image import (
    DirectGetImageParameters,
)
from local_console.core.commands.rpc_with_response import DirectCommandStatus
from local_console.core.schemas.schemas import DeviceConnection
from local_console.servers.webserver import AsyncWebserver
from local_console.servers.webserver import FileInbox

from tests.mocks.method_extend import MethodObserver
from tests.mocks.mock_paho_mqtt import MockMqttAgent
from tests.strategies.samplers.mqtt_message import MockMQTTMessage


@pytest.fixture
async def ready_camera(
    single_device_config, mocked_agent_fixture, nursery, monkeypatch
):
    config: DeviceConnection = single_device_config.devices[0]
    with (
        patch(
            "local_console.core.commands.rpc_with_response.random_id"
        ) as mock_random_id,
        patch(
            "local_console.core.camera.states.v2.imagecap.PreviewBuffer.update"
        ) as mock_preview,
        patch(
            "local_console.core.camera.states.v2.imagecap.ImageCapturingCameraV2._save_into_input_directory"
        ) as mock_save,
    ):
        camera = Camera(
            config,
            MagicMock(spec=trio.MemorySendChannel),
            MagicMock(spec=AsyncWebserver),
            MagicMock(spec=FileInbox),
            MagicMock(spec=trio.lowlevel.TrioToken),
            Mock(),
        )
        await nursery.start(camera.setup)
        await camera._transition_to_state(ReadyCameraV2(camera._common_properties))

        yield camera, config, mocked_agent_fixture, mock_random_id, mock_preview, mock_save

    mocked_agent_fixture.stop_receiving_messages()


def camera_will_return_image(
    mocked_agent: MockMqttAgent, rpc_id_mock: Mock, req_id: str, image_data: str
):
    response = json.dumps(
        {"res_info": {"code": 0, "detail_msg": ""}, "image": image_data}
    )
    rpc_id_mock.return_value = req_id
    mocked_agent.receives(
        MockMQTTMessage(
            topic=MQTTTopics.RPC_RESPONSES.value.replace("+", req_id),
            payload=json.dumps(
                {
                    "direct-command-response": {
                        "response": response,
                        "reqid": req_id,
                        "status": "ok",
                        "errorMessage": "",
                    }
                }
            ).encode("utf-8"),
        )
    )


@pytest.mark.trio
@patch("local_console.core.commands.rpc_with_response.Agent")
async def test_preview_start(rpc_agent_class_mock, ready_camera, monkeypatch):
    from local_console.core.camera.states.v2.imagecap import ImageCapturingCameraV2

    rpc_mocked_agent = MockMqttAgent(rpc_agent_class_mock)
    camera, config, mocked_agent, mock_random_id, mock_preview, mock_save = ready_camera

    obs_exit = MethodObserver(monkeypatch)
    obs_exit.hook(ReadyCameraV2, "exit")

    # Prepare expected camera response
    raw_image_data = b"fake_image_data1"
    encoded_image_data = b64encode(raw_image_data).decode()
    camera_will_return_image(
        rpc_mocked_agent, mock_random_id, "resp1", encoded_image_data
    )
    res = await camera.run_command(
        "$system", "direct_get_image", DirectGetImageParameters(), {"preview": True}
    )
    # ... and the state transition took place
    await obs_exit.wait_for()
    assert camera.current_state is ImageCapturingCameraV2

    # Check what was sent by the device
    assert encoded_image_data in res.direct_command_response.response
    # The image was saved to the preview buffer
    mock_preview.assert_called_once_with(raw_image_data)

    # Now that we're here, test a frame request by the frontend:
    mock_preview.reset_mock()
    raw_image_data = b"fake_image_data2"
    encoded_image_data = b64encode(raw_image_data).decode()
    camera_will_return_image(
        rpc_mocked_agent, mock_random_id, "resp2", encoded_image_data
    )
    res = await camera.run_command(
        "$system", "direct_get_image", DirectGetImageParameters(), {"preview": True}
    )
    assert encoded_image_data in res.direct_command_response.response

    # The image was saved to the preview buffer
    mock_preview.assert_called_once_with(raw_image_data)

    # No images were saved to the file system
    mock_save.assert_not_called()


@pytest.mark.trio
@patch("local_console.core.commands.rpc_with_response.Agent")
async def test_image_streaming_start(rpc_agent_class_mock, ready_camera, monkeypatch):
    from local_console.core.camera.states.v2.imagecap import ImageCapturingCameraV2

    rpc_mocked_agent = MockMqttAgent(rpc_agent_class_mock)
    camera, config, mocked_agent, mock_random_id, mock_preview, mock_save = ready_camera

    obs_exit = MethodObserver(monkeypatch)
    obs_exit.hook(ReadyCameraV2, "exit")

    # Prepare expected camera response
    raw_image_data = b"fake_image_data1"
    encoded_image_data = b64encode(raw_image_data).decode()
    camera_will_return_image(
        rpc_mocked_agent, mock_random_id, "resp1", encoded_image_data
    )
    res = await camera.run_command(
        "$system", "direct_get_image", DirectGetImageParameters(), {"preview": False}
    )
    # ... and the state transition took place
    await obs_exit.wait_for()
    assert camera.current_state is ImageCapturingCameraV2

    # Check what was sent by the device
    assert encoded_image_data in res.direct_command_response.response
    # The image was saved to the file system
    mock_save.assert_awaited_once_with(ANY, raw_image_data, ANY)

    # Now that we're here, test a frame request by the frontend:
    mock_save.reset_mock()
    raw_image_data = b"fake_image_data2"
    encoded_image_data = b64encode(raw_image_data).decode()
    camera_will_return_image(
        rpc_mocked_agent, mock_random_id, "resp2", encoded_image_data
    )
    res = await camera.run_command(
        "$system", "direct_get_image", DirectGetImageParameters(), {"preview": False}
    )
    assert encoded_image_data in res.direct_command_response.response

    # The image was saved to the file system
    mock_save.assert_awaited_once_with(ANY, raw_image_data, ANY)

    # No images were saved to the preview buffer
    mock_preview.assert_not_called()


@pytest.mark.trio
@patch("local_console.core.commands.rpc_with_response.Agent")
async def test_streaming_stop_trigger(rpc_agent_class_mock, ready_camera, monkeypatch):
    from local_console.core.camera.states.v2.imagecap import ImageCapturingCameraV2

    camera, config, mocked_agent, _, _, _ = ready_camera

    obs_exit = MethodObserver(monkeypatch)
    obs_exit.hook(ImageCapturingCameraV2, "exit")

    # The test starts at the streaming state
    monkeypatch.setattr(ImageCapturingCameraV2, "_get_frame", AsyncMock())
    await camera._transition_to_state(
        ImageCapturingCameraV2(camera._common_properties, {}, {})
    )

    # The FE emits this RPC...
    res = await camera.run_command(
        "$system", "direct_get_image", DirectGetImageParameters(), {"stop": True}
    )
    # ... and the state transition took place
    await obs_exit.wait_for()
    assert camera.current_state is ReadyCameraV2
    assert res.direct_command_response.status == DirectCommandStatus.OK
