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
from venv import logger

from mocked_device.device import MockDevice
from mocked_device.mock.rpc.filter import RPCCommand
from mocked_device.mock.rpc.filter import RPCFilter
from mocked_device.mock.rpc.streaming.state_machine import StateMachine
from mocked_device.mock.rpc.streaming.values import UploadingParams
from mocked_device.mock.topics import MqttTopics
from mocked_device.mqtt.event import TopicListener
from mocked_device.mqtt.values import MqttMessage
from mocked_device.mqtt.values import TargetedMqttMessage
from mocked_device.utils.json import json_bytes

logger = logging.getLogger(__name__)


class StreamingListener(TopicListener):
    def __init__(self, device: MockDevice):
        self._filter = RPCFilter()
        self._device = device
        self._state_machine = StateMachine()

    def topic(self) -> str:
        return self._filter.topic()

    def _accepted(self, command: RPCCommand) -> None:
        response_topic = MqttTopics.RPC_RESP.suffixed(command.message_id)
        json_payload = {"response": {"result": "Accepted"}}
        self._device.send_mqtt(
            MqttMessage(topic=response_topic, payload=json_bytes(json_payload))
        )

    def handle(self, message: TargetedMqttMessage) -> None:
        command = self._filter.filter(message)
        if command and command.method == "StartUploadInferenceData":
            params = UploadingParams.model_validate(command.params)
            logger.debug(f"Get payload {params}")
            self._state_machine.start_with(params)
            self._accepted(command)

        if command and command.method == "StopUploadInferenceData":
            self._state_machine.stop()
            self._accepted(command)
