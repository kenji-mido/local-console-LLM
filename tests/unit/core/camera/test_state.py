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
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from local_console.core.camera.mixin_mqtt import MQTTEvent
from local_console.core.camera.state import CameraState
from local_console.core.schemas.schemas import OnWireProtocol

from tests.fixtures.agent import mocked_agent
from tests.strategies.samplers.mqtt_message import MockMQTTMessage


@pytest.mark.trio
async def test_udpdate_of_last_reception() -> None:
    with mocked_agent() as mock_agent:

        topic = "v1/devices/me/rpc/response/1"
        payload = {
            "moduleInstance": "backdoor-EA_Main",
            "status": 0,
            "response": {"Result": "Succeeded", "Image": "BASE64IMAGE"},
        }

        msg = MockMQTTMessage(topic, json.dumps(payload).encode("utf-8"))
        mock_agent.send_messages([msg])
        state = CameraState(MagicMock(), MagicMock())
        state.mqtt_host.value = "host"
        state.mqtt_port.value = 1883
        state._onwire_schema = OnWireProtocol.EVP1
        observer_called = False

        def observer(new_event: MQTTEvent, _: MQTTEvent) -> None:
            nonlocal observer_called
            assert new_event.topic == topic
            assert new_event.payload == payload
            observer_called = True

        state.rpc_response.subscribe(observer)

        send = datetime.now()
        await state.mqtt_setup()

        assert observer_called
        reception_1 = state._last_reception
        assert state._last_reception
        assert send < state._last_reception

        state._process_camera_upload(b"", Path("mock_path"))

        assert reception_1 < state._last_reception
