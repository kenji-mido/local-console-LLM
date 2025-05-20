# Copyright 2024 Sony Semiconductor Solutions Corp.
#
# Licensed under the Apache License, Version 2.0 (the License);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an AS IS BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
from abc import ABC
from abc import abstractmethod

import pytest
import trio
from local_console.core.camera.state_guard import only_in_states
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes


@pytest.mark.trio
async def test_state_transition_injection(nursery):

    class InitialState:
        def __init__(self, transition_fn):
            self._transition = transition_fn

        async def receive(self, msg):
            if msg == "mid":
                new_state = IntermediateState(self._transition)
                await self._transition(new_state)

    class IntermediateState:
        def __init__(self, transition_fn):
            self._transition = transition_fn

        async def receive(self, msg):
            if msg == "back":
                new_state = InitialState(self._transition)
                await self._transition(new_state)
            elif msg == "next":
                new_state = FinalState(self._transition)
                await self._transition(new_state)

    class FinalState:
        def __init__(self, transition_fn):
            self._transition = transition_fn

        async def receive(self, msg):
            if msg == "back":
                new_state = IntermediateState(self._transition)
                await self._transition(new_state)

    ##############

    class Machine:
        def __init__(self):
            self._state = InitialState(self.transition)
            self._send_ch, self._recv_ch = trio.open_memory_channel(0)
            self._event = trio.Event()

        @property
        def state(self):
            return type(self._state)

        async def wait_transition(self):
            await self._event.wait()

        async def transition(self, new_state):
            self._state = new_state
            self._event.set()

        async def read_loop(self):
            async with self._recv_ch:
                async for msg in self._recv_ch:
                    await self._state.receive(msg)

        async def inject(self, msg):
            self._event = trio.Event()
            await self._send_ch.send(msg)

    machine = Machine()
    nursery.start_soon(machine.read_loop)
    assert machine.state is InitialState

    async with machine._send_ch:

        await machine.inject("boo")
        assert machine.state is InitialState

        await machine.inject("mid")
        await machine.wait_transition()
        assert machine.state is IntermediateState


def test_state_guard():

    class Base(ABC):
        @abstractmethod
        def trigger(self) -> str: ...

    class StCherry(Base):
        def trigger(self) -> str:
            return "Cherry"

    class StKiwi(Base):
        def trigger(self) -> str:
            return "Kiwi"

    class StPeach(Base):
        def trigger(self) -> str:
            return "Peach"

    class Machine:
        def __init__(self) -> None:
            self._state = StCherry()

        @only_in_states([StCherry, StPeach])
        def run_trigger(self) -> str:
            return self._state.trigger()

        def transition(self) -> None:
            current = type(self._state)
            if current is StCherry:
                self._state = StKiwi()
            elif current is StKiwi:
                self._state = StPeach()
            elif current is StPeach:
                self._state = StCherry()

    fsm = Machine()

    # Assert allowed method call
    assert fsm.run_trigger() == "Cherry"

    # Assert disallowed method call
    fsm.transition()
    with pytest.raises(UserException) as error:
        fsm.run_trigger()

        assert (
            str(error.value)
            == "Attempted to invoke method run_trigger while camera is in state StKiwi, which is not in the allowed set: ['StCherry', 'StPeach']"
        )
        assert error.value.code == ErrorCodes.EXTERNAL_INVALID_METHOD_DURING_STATE

    # Assert a further allowed method call
    fsm.transition()
    assert fsm.run_trigger() == "Peach"
