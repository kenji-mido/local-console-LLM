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

import trio
from local_console.core.schemas.schemas import OnWireProtocol

from tests.strategies.samplers.mqtt_message import MockMQTTMessage


class MockAsyncIterator:
    def __init__(self, seq: list[MockMQTTMessage], keep_running: bool = False) -> None:
        self.messages = seq
        self.more_messages = trio.Event()
        self._keep_running = keep_running

    def __aiter__(self):
        return self

    async def __anext__(self) -> MockMQTTMessage:
        while len(self.messages) <= 0 and self.keep_running:
            await self.more_messages.wait()
        if len(self.messages) > 0:
            return self.messages.pop()
        raise StopAsyncIteration

    def extend(self, messages: list[MockMQTTMessage]) -> None:
        self.messages.extend(messages)
        self.more_messages.set()

    @property
    def keep_running(self):
        return self._keep_running

    @keep_running.setter
    def keep_running(self, value: bool):
        self._keep_running = value
        self.more_messages.set()


class MockAsyncContext:
    def __init__(self, seq: list[MockMQTTMessage]):
        self.iterator = MockAsyncIterator(seq)

    async def __aenter__(self):
        return self.iterator

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def extend(self, messages: list[MockMQTTMessage]) -> None:
        # Extend the current sequence of messages
        self.iterator.extend(messages)


class MockMqttAgent:
    def __init__(self, constructor: MagicMock, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.constructor = constructor
        self.agent = MagicMock()
        constructor.return_value = self.agent
        self.agent.publish = AsyncMock()
        self.agent.rpc = AsyncMock()
        self.agent.configure = AsyncMock()
        self.agent.onwire_schema = OnWireProtocol.EVP1
        self.agent.deploy = AsyncMock()

    def has_been_called(self) -> bool:
        return self.constructor.call_count > 0

    def has_been_initialized_on_port(self, port: int = 1883) -> None:
        call = self.constructor.mock_calls[0]
        assert call.args[0] == "localhost"
        assert call.args[1] == port

    def _get_message_mocker(self) -> MockAsyncContext:
        context = self.agent.client.messages.return_value
        if not isinstance(context, MockAsyncContext):
            context = MockAsyncContext([])
            self.agent.client.messages.return_value = context
        return context

    @property
    def wait_for_messages(self):
        return self._get_message_mocker().iterator.keep_running

    @wait_for_messages.setter
    def wait_for_messages(self, value: bool):
        self._get_message_mocker().iterator.keep_running = value

    def send_messages(self, messages: list[MockMQTTMessage]) -> None:
        # Handle existing context or create a new one
        self._get_message_mocker().extend(messages)
