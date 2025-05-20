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
from collections.abc import Awaitable
from collections.abc import Coroutine
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from typing import Callable
from typing import Optional
from typing import Protocol
from typing import Self

import trio
from local_console.clients.agent import Agent
from local_console.core.camera.enums import MQTTTopics
from local_console.core.camera.schemas import PropertiesReport
from local_console.core.schemas.schemas import DeviceConnection
from local_console.core.schemas.schemas import DeviceID
from local_console.core.schemas.schemas import DeviceType
from local_console.servers.broker import spawn_broker
from local_console.servers.webserver import AsyncWebserver
from local_console.servers.webserver import FileInbox
from local_console.utils.fstools import StorageSizeWatcher
from local_console.utils.timing import now
from pydantic import BaseModel
from trio import MemorySendChannel
from trio import TASK_STATUS_IGNORED
from trio.lowlevel import TrioToken

logger = logging.getLogger(__name__)


class MQTTEvent(BaseModel):
    topic: str
    payload: dict[str, Any]


class State(Protocol):
    """
    TypeState classes must adhere to this protocol
    """

    async def enter(self, nursery: trio.Nursery) -> None:
        """
        This method implements the transition into the state. It can be
        leveraged to spawn work in the background that supports the state's
        logic.
        """

    async def exit(self) -> None:
        """
        This method implements the transition out of the state. It can be
        leveraged to perform custom clean up or termination actions before
        the next state's `enter` method is awaited.
        """

    async def on_message_received(self, message: MQTTEvent) -> None:
        """
        This method performs actions based on incoming messages over MQTT.
        """


# Signature for functions that process incoming MQTT messages
MQTTMessageFunc = Callable[[MQTTEvent], Coroutine[Any, Any, None]]


class MQTTDriver:
    """
    This object manages the MQTT broker and the main MQTT client for
    interacting with a camera as it transitions over its set of
    possible states. It delegates message processing to a dynamically
    assigned function, which shall be provided by the implementation
    of the current camera state.
    """

    def __init__(self, config: DeviceConnection) -> None:
        self._mqtt_port: int = config.mqtt.port
        self.client = Agent(self._mqtt_port)
        self._last_reception: Optional[datetime] = None
        self._message_handler: Optional[MQTTMessageFunc] = None

    async def setup(self, *, task_status: Any = TASK_STATUS_IGNORED) -> None:
        async with (
            trio.open_nursery() as nursery,
            spawn_broker(self._mqtt_port, nursery, False),
            self.client.mqtt_scope(
                [
                    MQTTTopics.ATTRIBUTES.value,
                    MQTTTopics.ATTRIBUTES_REQ.value,
                    MQTTTopics.TELEMETRY.value,
                ]
            ),
        ):
            assert self.client.client
            task_status.started(True)
            logger.debug(f"Broker started up and listening on port {self._mqtt_port}")
            async with self.client.client.messages() as mgen:
                async for msg in mgen:
                    self._last_reception = now()

                    if self._message_handler:
                        await self._message_handler(
                            MQTTEvent(topic=msg.topic, payload=json.loads(msg.payload))
                        )

    def set_handler(self, handler: MQTTMessageFunc) -> None:
        self._message_handler = handler


@dataclass
class BaseStateProperties:
    id: DeviceID
    mqtt_drv: MQTTDriver
    webserver: AsyncWebserver
    file_inbox: FileInbox
    transition_fn: "TransitionFunc"
    trio_token: TrioToken
    message_send_channel: MemorySendChannel
    dirs_watcher: StorageSizeWatcher
    device_type: DeviceType
    reported: PropertiesReport
    on_report_fn: Callable[[DeviceID, PropertiesReport], None]


class StateWithProperties(State):

    def __init__(self, base: BaseStateProperties) -> None:
        self._state_properties = base

    @property
    def _id(self) -> DeviceID:
        return self._state_properties.id

    @property
    def _mqtt(self) -> MQTTDriver:
        return self._state_properties.mqtt_drv

    @property
    def _http(self) -> AsyncWebserver:
        return self._state_properties.webserver

    @property
    def _file_inbox(self) -> FileInbox:
        return self._state_properties.file_inbox

    @property
    def _transit_to(self) -> "TransitionFunc":
        return self._state_properties.transition_fn

    @property
    def _trio_token(self) -> TrioToken:
        return self._state_properties.trio_token

    @property
    def _message_send_channel(self) -> MemorySendChannel:
        return self._state_properties.message_send_channel

    @property
    def _dirs_watcher(self) -> StorageSizeWatcher:
        return self._state_properties.dirs_watcher

    @property
    def _device_type(self) -> DeviceType:
        return self._state_properties.device_type

    @property
    def _props_report(self) -> PropertiesReport:
        return self._state_properties.reported


# Signature for state transition functions
TransitionFunc = Callable[[StateWithProperties], Awaitable[None]]


class Uninitialized(StateWithProperties):
    """
    Used as a placeholder for an unassigned state (e.g. a "null" state).
    """

    @classmethod
    def new(cls) -> Self:
        return cls(BaseStateProperties(*[None] * 11))  # type: ignore
