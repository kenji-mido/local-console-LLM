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
import logging

from mocked_device.mqtt.event import TopicListener
from mocked_device.mqtt.values import TargetedMqttMessage

logger = logging.getLogger(__name__)


class MessageRouter:
    def __init__(self) -> None:
        self._listeners: list[TopicListener] = []

    def route(self, message: TargetedMqttMessage) -> None:
        for listener in self._listeners:
            listener.handle(message)

    def add_handler(self, handler: TopicListener) -> None:
        self._listeners.append(handler)

    def remove_handler(self, handler: TopicListener) -> None:
        self._listeners.remove(handler)
