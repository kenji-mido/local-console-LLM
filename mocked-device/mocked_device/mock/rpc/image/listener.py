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
from mocked_device.device import MockDevice
from mocked_device.mock.rpc.fake import fake_image_base64
from mocked_device.mock.rpc.filter import RPCFilter
from mocked_device.mock.topics import MqttTopics
from mocked_device.mqtt.event import TopicListener
from mocked_device.mqtt.values import MqttMessage
from mocked_device.mqtt.values import TargetedMqttMessage
from mocked_device.utils.json import json_bytes


class ImageListener(TopicListener):
    def __init__(self, device: MockDevice):
        self._filter = RPCFilter()
        self._device = device

    def topic(self) -> str:
        return self._filter.topic()

    def handle(self, message: TargetedMqttMessage) -> None:
        command = self._filter.filter(message)
        if command and command.method == "DirectGetImage":
            response_topic = MqttTopics.RPC_RESP.suffixed(command.message_id)
            json_payload = {"response": {"Image": fake_image_base64()}}
            self._device.send_mqtt(
                MqttMessage(topic=response_topic, payload=json_bytes(json_payload))
            )
