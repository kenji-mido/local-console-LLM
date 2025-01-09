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
import logging
from venv import logger

import pytest
import trio
from fastapi import status
from httpx import AsyncClient
from local_console.utils.trio import EVENT_WAITING
from local_console.utils.trio import TimeoutConfig

from tests.fixtures.agent import mocked_agent_fixture
from tests.fixtures.configs import stored_devices
from tests.fixtures.fastapi import fa_client_with_agent
from tests.mocks.mock_paho_mqtt import MockMqttAgent
from tests.strategies.samplers.configs import DeviceConnectionSampler
from tests.strategies.samplers.mqtt_message import MockMQTTMessage

logger = logging.getLogger(__name__)


@pytest.mark.trio
async def test_send_start_streaming_inference(
    fa_client_with_agent: AsyncClient,
    mocked_agent_fixture: MockMqttAgent,
) -> None:

    app = fa_client_with_agent._transport.app
    expected_devices = DeviceConnectionSampler().list_of_samples(1)
    dev = expected_devices[0]
    dev_id = dev.mqtt.port
    rpc_returned = False
    with stored_devices(expected_devices, app.state.device_service):
        mqtt_client = mocked_agent_fixture
        mqtt_client.wait_for_messages = True
        async with trio.open_nursery() as nursery:

            async def start_inference() -> None:
                nonlocal rpc_returned
                response = await fa_client_with_agent.post(
                    f"/devices/{dev_id}/modules/$system/command",
                    json={
                        "command_name": "StartUploadInferenceData",
                        "parameters": {
                            "CropHOffset": 123,
                            "CropVOffset": 234,
                            "CropHSize": 3987,
                            "CropVSize": 2987,
                        },
                    },
                )
                assert response.status_code == status.HTTP_200_OK
                rpc_response = response.json()
                assert rpc_response["result"] == "SUCCESS"
                assert rpc_response["command_response"]["mocked"] == "response"
                rpc_returned = True

            nursery.start_soon(start_inference)

            def rpc_publish_message() -> bool:
                logger.debug("Wait for publish to be called")
                return mqtt_client.agent.publish.await_count > 0

            await TimeoutConfig(timeout_in_seconds=3).wait_for(rpc_publish_message)
            assert mqtt_client.agent.publish.await_count > 0
            rpc_args, _ = mqtt_client.agent.publish.await_args
            topic = rpc_args[0]
            payload = json.loads(rpc_args[1])
            assert payload["method"] == "ModuleMethodCall"
            assert payload["params"]["moduleMethod"] == "StartUploadInferenceData"
            assert payload["params"]["moduleInstance"] == "backdoor-EA_Main"
            assert payload["params"]["params"]["StorageSubDirectoryPath"] == "images"
            assert (
                payload["params"]["params"]["StorageSubDirectoryPathIR"] == "inferences"
            )
            assert (
                payload["params"]["params"]["StorageName"] == "http://web.server:None"
            )
            assert (
                payload["params"]["params"]["StorageNameIR"] == "http://web.server:None"
            )
            assert payload["params"]["params"]["CropHOffset"] == 123
            assert payload["params"]["params"]["CropVOffset"] == 234
            assert payload["params"]["params"]["CropHSize"] == 3987
            assert payload["params"]["params"]["CropVSize"] == 2987
            assert topic.startswith("v1/devices/me/rpc/request")
            request_id = topic.split("/")[-1]
            msg = MockMQTTMessage(
                topic=f"v1/devices/me/rpc/response/{request_id}",
                payload=json.dumps({"response": {"mocked": "response"}}).encode(
                    "utf-8"
                ),
            )
            mqtt_client.send_messages([msg])
            await EVENT_WAITING.wait_for(lambda: rpc_returned)
            mqtt_client.wait_for_messages = False
        assert rpc_returned
