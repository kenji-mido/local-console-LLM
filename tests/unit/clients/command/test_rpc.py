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
from unittest.mock import AsyncMock

import pytest
from local_console.clients.command.rpc import RPCArgument
from local_console.clients.command.rpc import RPCEVP1
from local_console.clients.command.rpc import RPCEVP2
from local_console.core.schemas.schemas import OnWireProtocol
from paho.mqtt.client import MQTT_ERR_SUCCESS


def mocked_client(response: str = MQTT_ERR_SUCCESS) -> AsyncMock:
    client = AsyncMock()
    client.publish.return_value = (response, None)
    return client


@pytest.mark.trio
async def test_evp1_send_params_as_dict():
    arg = RPCArgument(
        onwire_schema=OnWireProtocol.EVP1,
        instance_id="instance",
        method="method",
        params={"param": "value"},
    )
    client = mocked_client()
    command = RPCEVP1(client)
    response = await command.run(arg)
    expected_payload = json.dumps(
        {
            "method": "ModuleMethodCall",
            "params": {
                "moduleMethod": arg.method,
                "moduleInstance": arg.instance_id,
                "params": arg.params,
            },
        },
    )

    client.publish.assert_called_once_with(
        f"v1/devices/me/rpc/request/{response.response_id}", expected_payload
    )


@pytest.mark.trio
async def test_evp2_send_params_as_string():
    arg = RPCArgument(
        onwire_schema=OnWireProtocol.EVP2,
        instance_id="instance",
        method="method",
        params={"param": "value"},
    )
    client = mocked_client()
    command = RPCEVP2(client)
    response = await command.run(arg)
    expected_payload = json.dumps(
        {
            "method": "ModuleMethodCall",
            "params": {
                "direct-command-request": {
                    "reqid": response.response_id,
                    "method": arg.method,
                    "instance": arg.instance_id,
                    "params": json.dumps(arg.params),
                }
            },
        },
    )

    client.publish.assert_called_once_with(
        f"v1/devices/me/rpc/request/{response.response_id}", expected_payload
    )
