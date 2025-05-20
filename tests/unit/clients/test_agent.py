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
from unittest.mock import ANY
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st
from local_console.clients.agent import Agent
from local_console.core.camera.enums import MQTTTopics
from local_console.core.helpers import check_attributes_request
from paho.mqtt.client import MQTT_ERR_ERRNO
from paho.mqtt.client import MQTT_ERR_SUCCESS

from tests.strategies.configs import generate_text


@pytest.mark.trio
async def test_mqtt_scope_error_handling(caplog):
    with (patch("local_console.clients.agent.AsyncClient") as mock_aclient,):
        mock_aclient.return_value.connect.side_effect = ValueError("Error from Paho")

        agent = Agent(ANY)
        with pytest.raises(SystemExit):
            async with agent.mqtt_scope([]):
                # The connection being unsuccessful makes what
                # happens here unreachble and hence irrelevant.
                pass

        assert "Exception occurred within MQTT client processing" in caplog.text
        assert "Error from Paho" in caplog.text


@given(
    generate_text(),
    generate_text(),
)
@pytest.mark.trio
async def test_publish(
    topic: str,
    config: str,
):
    with (
        patch("local_console.clients.agent.paho.Client"),
        patch("local_console.clients.agent.AsyncClient") as mock_client,
    ):
        mock_client.return_value.publish_and_wait = AsyncMock()
        mock_client.return_value.publish_and_wait.return_value = [MQTT_ERR_SUCCESS]

        agent = Agent(ANY)
        async with agent.mqtt_scope([]):
            await agent.publish(topic, config)

        mock_client.return_value.publish_and_wait.assert_awaited_once_with(
            topic, payload=config
        )


@given(
    generate_text(),
    generate_text(),
)
@pytest.mark.trio
async def test_publish_error(
    topic: str,
    config: str,
):
    with (
        patch("local_console.clients.agent.paho.Client"),
        patch("local_console.clients.agent.AsyncClient") as mock_client,
    ):
        mock_client.return_value.publish_and_wait = AsyncMock()
        mock_client.return_value.publish_and_wait.return_value = [MQTT_ERR_ERRNO]

        agent = Agent(ANY)
        with pytest.raises(SystemExit):
            async with agent.mqtt_scope([]):
                await agent.publish(topic, config)

            mock_client.return_value.publish_and_wait.assert_awaited_once_with(
                topic, payload=config
            )


@given(st.integers(min_value=1))
@pytest.mark.trio
async def test_attributes_request_handling(mqtt_req_id: int):
    with (
        patch("local_console.clients.agent.paho.Client"),
        patch("local_console.clients.agent.AsyncClient"),
    ):
        request_topic = MQTTTopics.ATTRIBUTES_REQ.value.replace("+", str(mqtt_req_id))

        agent = Agent(ANY)
        agent.publish = AsyncMock()
        async with agent.mqtt_scope([MQTTTopics.ATTRIBUTES_REQ.value]):
            check = await check_attributes_request(agent, request_topic, "{}")

        response_topic = request_topic.replace("request", "response")
        agent.publish.assert_called_once_with(response_topic, "{}")
        assert check
