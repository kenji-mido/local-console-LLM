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
from collections import deque
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import trio
from local_console.core.schemas.schemas import OnWireProtocol

from tests.strategies.samplers.mqtt_message import MockMQTTMessage


class MockAsyncIterator:
    def __init__(self) -> None:
        self._messages: deque[MockMQTTMessage] = deque(maxlen=10)
        self._accepting_messages = True
        self._event = trio.Event()
        self._has_been_read = trio.Event()

    def __aiter__(self):
        return self

    async def __anext__(self) -> MockMQTTMessage:
        if self._accepting_messages:
            try:
                await self._event.wait()
                gotten = self._messages.popleft()

                self._event = trio.Event()
                if len(self._messages) > 0:
                    self._event.set()

                self._has_been_read.set()
                return gotten
            except IndexError:
                pass

        raise StopAsyncIteration

    def receives(self, message: MockMQTTMessage) -> None:
        self._messages.append(message)
        self._has_been_read = trio.Event()
        self._event.set()

    def stop(self) -> None:
        self._accepting_messages = False
        self._event.set()

    async def wait_to_be_read(self) -> None:
        await self._has_been_read.wait()


class MockAsyncContext:
    def __init__(self):
        iterator = MockAsyncIterator()
        self.iterator = iterator

    async def __aenter__(self):
        return self.iterator

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


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

        self._msg_in = MockAsyncContext()
        self.agent.client.messages.return_value = self._msg_in

    def has_been_called(self) -> bool:
        return self.constructor.call_count > 0

    def has_been_initialized_on_port(self, port: int = 1883) -> None:
        call = self.constructor.mock_calls[0]
        assert call.args[0] == port

    def stop_receiving_messages(self):
        self._msg_in.iterator.stop()

    def receives(self, message: MockMQTTMessage) -> None:
        self._msg_in.iterator.receives(message)

    async def wait_message_to_be_read(self) -> None:
        await self._msg_in.iterator.wait_to_be_read()
