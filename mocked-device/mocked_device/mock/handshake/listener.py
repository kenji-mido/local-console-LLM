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
from mocked_device.mock.topics import MqttTopics
from mocked_device.mqtt.event import TopicListener
from mocked_device.mqtt.values import TargetedMqttMessage


class HandshakeListener(TopicListener):
    def __init__(self, message_id: str) -> None:
        self.message_id = message_id
        self._topic = MqttTopics.ATTRIBUTES_REQ.suffixed(message_id)
        self.finished = False

    def topic(self) -> str:
        return self._topic

    def handle(self, message: TargetedMqttMessage) -> None:
        if message.topic == self._topic:
            self.finished = True
