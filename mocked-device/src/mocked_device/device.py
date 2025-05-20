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
from abc import ABC
from abc import abstractmethod
from collections.abc import Sequence
from enum import Enum
from typing import Any

from mocked_device.message_base import MessageBuilder
from mocked_device.mqtt.connection import MqttConnection
from mocked_device.mqtt.event import TopicListener
from mocked_device.mqtt.values import MqttMessage
from pydantic import BaseModel


class AppStates(Enum):
    Classification = "classification"
    Detection = "detection"
    ZoneDetection = "zone"
    Empty = "empty"


class DeviceAssets(BaseModel):
    application: AppStates = AppStates.Empty


class MockDevice(ABC):

    def __init__(self, conn: MqttConnection, listeners: Sequence[type[TopicListener]]):
        self._conn = conn
        self.device_assets: DeviceAssets = DeviceAssets()
        self.status: MessageBuilder
        self.event_log: MessageBuilder
        self.__add_listeners(listeners)

    def __add_listeners(self, listeners: Sequence[type[TopicListener]]) -> None:
        for listener in listeners:
            self._conn.add_listener(listener(self))  # type: ignore [call-arg]

    def send_mqtt(self, message: MqttMessage) -> None:
        myself = self._conn.config
        self._conn.publish(message.target_to(myself))

    def send_status(self) -> None:
        self.send_mqtt(self.status.build())

    def send_event_log(self) -> None:
        self.send_mqtt(self.event_log.build())

    @abstractmethod
    def do_handshake(self) -> None: ...

    @abstractmethod
    def update_edge_app(self, content: Any) -> None: ...

    @abstractmethod
    def reboot(self, command: Any) -> None: ...

    @abstractmethod
    def send_direct_image(self, command: Any) -> None: ...

    @abstractmethod
    def send_accepted(self, command: Any) -> None: ...
