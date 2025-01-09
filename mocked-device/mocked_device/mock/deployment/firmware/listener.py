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
import base64
import json
import logging
from typing import Any

from mocked_device.device import MockDevice
from mocked_device.mock.deployment.firmware.state_machine import StateMachine
from mocked_device.mock.topics import MqttTopics
from mocked_device.mqtt.event import TopicListener
from mocked_device.mqtt.values import TargetedMqttMessage
from mocked_device.utils.json import get_field

logger = logging.getLogger(__name__)

MODULE = "configuration/backdoor-EA_Main/placeholder"


class FirmwareListener(TopicListener):
    def __init__(self, device: MockDevice):
        self._state_machine = StateMachine(device)

    def topic(self) -> str:
        return MqttTopics.ATTRIBUTES.value

    def _filter(self, message: TargetedMqttMessage) -> dict[str, Any] | None:
        if message.topic != self.topic():
            return None
        json_payload = json.loads(message.payload)
        if MODULE not in json_payload:
            return None
        content = base64.b64decode(
            json_payload["configuration/backdoor-EA_Main/placeholder"]
        ).decode("utf-8")
        json_content = json.loads(content)
        return {MODULE: json_content}

    def handle(self, message: TargetedMqttMessage) -> None:
        logger.debug(
            f"Received firmware update request {message.payload.decode('utf-8')}"
        )
        content = self._filter(message)
        if not content:
            logger.debug("This is not a firmware deploy message")
            return
        package_uri = get_field(content, f"{MODULE}.OTA.PackageUri") or ""
        if not isinstance(package_uri, str):
            logger.error("Invalid package URI in firmware deployment")
        else:
            logger.debug(f"Adding uri to process {package_uri}")
            self._state_machine.new_event(package_uri)
