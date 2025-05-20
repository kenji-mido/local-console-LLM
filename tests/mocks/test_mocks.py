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

import pytest
import trio

from tests.mocks.method_extend import extend_method
from tests.mocks.method_extend import extend_method_async
from tests.mocks.method_extend import MethodObserver
from tests.mocks.mock_paho_mqtt import MockAsyncIterator
from tests.strategies.samplers.mqtt_message import MockMQTTMessage


@pytest.mark.trio
async def test_async_mock_iterator(nursery):

    it = MockAsyncIterator()

    # test helper objects
    send_channel, receive_channel = trio.open_memory_channel(0)
    finished = trio.Event()

    async def fetch_task(signal: trio.Event):
        async for msg in it:
            await send_channel.send(msg)

        signal.set()

    nursery.start_soon(fetch_task, finished)

    msg = MockMQTTMessage(topic="whatever", payload="one")
    it.receives(msg)
    gotten = await receive_channel.receive()
    assert gotten.payload == msg.payload

    msg = MockMQTTMessage(topic="don't care", payload="baz")
    it.receives(msg)
    gotten = await receive_channel.receive()
    assert msg.payload == gotten.payload

    msg1 = MockMQTTMessage(topic="some", payload="content-1")
    msg2 = MockMQTTMessage(topic="some", payload="content-2")
    it.receives(msg1)
    it.receives(msg2)
    gotten = await receive_channel.receive()
    assert gotten.payload == msg1.payload
    gotten = await receive_channel.receive()
    assert gotten.payload == msg2.payload

    it.stop()
    await finished.wait()
    assert finished.is_set()


def test_method_extension(monkeypatch):

    class MyClass:
        def my_method(self):
            return 42

    def extension_logic(self, result):
        self.extra_attr = result * 2

    # Initial setup
    obj = MyClass()
    assert not hasattr(obj, "extra_attr")

    # Patch MyClass.my_method and check its effects
    extend_method(MyClass, "my_method", extension_logic, monkeypatch)
    result = obj.my_method()
    assert result == 42  # The original return value
    assert obj.extra_attr == 84


@pytest.mark.trio
async def test_method_extension_async(monkeypatch):

    class MyClass:
        async def my_method(self):
            return 42

    obj = MyClass()

    mock_my_method = AsyncMock()
    extend_method_async(MyClass, "my_method", mock_my_method, monkeypatch)
    result = await obj.my_method()
    assert result == 42
    mock_my_method.assert_awaited_once_with(obj, 42)


@pytest.mark.trio
async def test_async_method_observation(monkeypatch, nursery, autojump_clock):

    class MyClass:
        data = 0

        async def my_method(self):
            # Simulate a processing window
            await trio.sleep(5)

            self.data += 1

    # Patch MyClass.my_method and check its effects
    obs = MethodObserver(monkeypatch)
    obs.hook(MyClass, "my_method")

    # Initial setup
    obj = MyClass()
    assert obj.data == 0

    # Test for repeated usage of the observer
    for i in range(1, 5):
        nursery.start_soon(obj.my_method)
        await obs.wait_for()
        assert obj.data == i  # Expected execution side effect
