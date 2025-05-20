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
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from local_console.core.camera.enums import MQTTTopics
from local_console.core.camera.states.common import IdentifyingCamera
from local_console.core.camera.states.v2.common import ConnectedCameraStateV2
from local_console.core.camera.states.v2.ready import ReadyCameraV2
from local_console.core.camera.v2.components.device_info import AIModel
from local_console.core.commands.rpc_with_response import DirectCommandResponseBody
from local_console.core.commands.rpc_with_response import DirectCommandStatus
from local_console.core.config import Config
from local_console.core.schemas.schemas import DeviceType

from tests.mocks.method_extend import MethodObserver
from tests.mocks.mock_paho_mqtt import MockMqttAgent
from tests.strategies.samplers.mqtt_message import MockMQTTMessage
from tests.strategies.samplers.strings import random_int
from tests.strategies.samplers.strings import random_text


@pytest.mark.trio
async def test_send_configuration(nursery, camera, mocked_agent_fixture: MockMqttAgent):
    await nursery.start(camera.setup)

    state = ConnectedCameraStateV2(camera._common_properties)
    await camera._transition_to_state(state)

    data = {
        "req_info": {"req_id": random_text()},
        "custom_settings": {"property1": "value1"},
    }

    await camera.send_configuration("node", "edge_app", data)

    payload = {"configuration/node/edge_app": json.dumps(data)}
    mocked_agent_fixture.agent.publish.assert_called_once_with(
        "v1/devices/me/attributes", payload=json.dumps(payload)
    )


@pytest.mark.trio
async def test_run_command_no_response(
    nursery, camera, mocked_agent_fixture: MockMqttAgent
):
    await nursery.start(camera.setup)

    state = ConnectedCameraStateV2(camera._common_properties)
    await camera._transition_to_state(state)

    # force no message
    mocked_agent_fixture.stop_receiving_messages()

    res = await camera.run_command("node", "dummy_command", {}, {})
    assert (
        DirectCommandResponseBody(
            response="",
            reqid="",
            status=DirectCommandStatus.ERROR,
            errorMessage="Timeout",
        )
        == res.direct_command_response
    )


@pytest.mark.trio
@patch("local_console.core.commands.rpc_with_response.random_id", return_value="1111")
async def test_run_command_with_response(mock_random_id, nursery, camera):
    agent_class_mock = MagicMock()
    mocked_agent = MockMqttAgent(agent_class_mock)

    with (
        patch("local_console.core.commands.rpc_with_response.Agent", agent_class_mock),
    ):
        await nursery.start(camera.setup)

        state = ConnectedCameraStateV2(camera._common_properties)
        await camera._transition_to_state(state)

        rpc_id = mock_random_id()
        response = "direct command specific response"

        mocked_agent.receives(
            MockMQTTMessage(
                topic=MQTTTopics.RPC_RESPONSES.value.replace("+", rpc_id),
                payload=json.dumps(
                    {
                        "direct-command-response": {
                            "response": response,
                            "reqid": rpc_id,
                            "status": "ok",
                            "errorMessage": "",
                        }
                    }
                ).encode("utf-8"),
            )
        )

        res = await camera.run_command("node", "dummy_command", {}, {})

        assert (
            DirectCommandResponseBody(
                response=response,
                reqid=rpc_id,
                status=DirectCommandStatus.OK,
                errorMessage="",
            )
            == res.direct_command_response
        )


@pytest.mark.trio
async def test_private_endpoint_settings_updates_configuration(
    nursery, camera, mocked_agent_fixture: MockMqttAgent
):
    await nursery.start(camera.setup)

    state = ConnectedCameraStateV2(camera._common_properties)
    await camera._transition_to_state(state)

    host = random_text()
    port = random_int(0, 65535)

    msg = MockMQTTMessage(
        topic="v1/devices/me/attributes",
        payload=json.dumps(
            {
                "state/$system/PRIVATE_endpoint_settings": {
                    "req_info": {"req_id": ""},
                    "endpoint_url": host,
                    "endpoint_port": port,
                    "protocol_version": "TB",
                    "res_info": {"res_id": "", "code": 0, "detail_msg": "ok"},
                }
            }
        ),
    )

    mocked_agent_fixture.receives(msg)
    await mocked_agent_fixture.wait_message_to_be_read()
    # Ensure original configuration is applied
    mocked_agent_fixture.receives(msg)
    await mocked_agent_fixture.wait_message_to_be_read()

    config = Config().get_device_config(camera.id)
    assert config.mqtt.host == host
    assert config.mqtt.port == port


@pytest.mark.trio
async def test_identifying(
    nursery, camera, mocked_agent_fixture: MockMqttAgent, monkeypatch
):
    await nursery.start(camera.setup)

    obs = MethodObserver(monkeypatch)
    obs.hook(IdentifyingCamera, "on_message_received")

    state = IdentifyingCamera(camera._common_properties)
    await camera._transition_to_state(state)

    msg = MockMQTTMessage(
        topic="v1/devices/me/attributes",
        payload=json.dumps(
            {
                "systemInfo": {
                    "os": "NuttX",
                    "arch": "xtensa",
                    "evp_agent": "v1.40.0",
                    "evp_agent_commit_hash": "19ba152d5ad174999ac3a0e669eece54b312e5d1",
                    "wasmMicroRuntime": "v2.1.0",
                    "protocolVersion": "EVP2-TB",
                },
                "state/$system/device_info": {
                    "device_manifest": "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJBSVRSSU9TQ2VydFVVSUQiOiJBaWQtMDAwMTAwMDEtMDAwMC0yMDAwLTkwMDItMDAwMDAwMDAwMWQxIiwiaWF0IjoxNzQ3MzA4MDMxfQ.xGa42ZKJQ3G3R4o5K0PBAnT4rUfntwfGFO_HJY0RHgher2aApTX_pmHoyNOkaVXAmuTDWZIAGN4ENIpvMs9seA",
                    "chips": [],
                },
            }
        ),
    )

    mocked_agent_fixture.receives(msg)
    await mocked_agent_fixture.wait_message_to_be_read()
    await obs.wait_for()

    assert camera.current_state is ReadyCameraV2
    assert camera._common_properties.device_type == DeviceType.T3P_SZP


@pytest.mark.trio
async def test_undeploy_ai_models(
    nursery, camera, mocked_agent_fixture: MockMqttAgent, monkeypatch
):
    await nursery.start(camera.setup)

    obs = MethodObserver(monkeypatch)
    obs.hook(ConnectedCameraStateV2, "on_message_received")

    # step 1: device has a model
    camera._common_properties.reported.dnn_versions = ["1234"]

    state = ConnectedCameraStateV2(camera._common_properties)
    await camera._transition_to_state(state)

    device_info = {
        "state/$system/device_info": {
            "device_manifest": "",
            "chips": [
                {
                    "name": "sensor_chip",
                    "id": "100A50500A2012062364012000000000",
                    "hardware_version": "1",
                    "temperature": 34,
                    "loader_version": "020301",
                    "loader_hash": "",
                    "update_date_loader": "1970-01-01T00:00:06.000Z",
                    "firmware_version": "820204",
                    "firmware_hash": "",
                    "update_date_firmware": "1970-01-01T00:00:06.000Z",
                    "ai_models": [],
                }
            ],
        },
    }

    mocked_agent_fixture.receives(
        MockMQTTMessage(
            topic="v1/devices/me/attributes",
            payload=json.dumps(device_info),
        )
    )
    await obs.wait_for()

    # step 2: device has no model
    assert camera._common_properties.reported.dnn_versions == []

    device_info["state/$system/device_info"]["chips"][0]["ai_models"] = [
        AIModel(version="1", hash="2", update_date="3").model_dump()
    ]
    mocked_agent_fixture.receives(
        MockMQTTMessage(
            topic="v1/devices/me/attributes",
            payload=json.dumps(device_info),
        )
    )
    await obs.wait_for()

    # step 3: again, the device has a model deployed
    assert camera._common_properties.reported.dnn_versions == ["1"]
