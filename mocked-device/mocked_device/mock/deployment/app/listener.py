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

from mocked_device import device
from mocked_device.device import MockDevice
from mocked_device.mock.deployment.app.value import DeploymentConfig
from mocked_device.mock.topics import MqttTopics
from mocked_device.mqtt.event import TopicListener
from mocked_device.mqtt.values import MqttMessage
from mocked_device.mqtt.values import TargetedMqttMessage
from mocked_device.utils.json import json_bytes
from mocked_device.utils.request import download

logger = logging.getLogger(__name__)

DEPLOYMENT = "deployment"


class AppListener(TopicListener):
    def __init__(self, device: MockDevice):
        self._device = device

    def topic(self) -> str:
        return MqttTopics.ATTRIBUTES.value

    def _filter(self, message: TargetedMqttMessage) -> DeploymentConfig | None:
        if message.topic != self.topic():
            return None
        try:
            json_payload = json.loads(message.payload)
            if not DEPLOYMENT in json_payload:
                return None
            deployment_json = json.loads(json_payload[DEPLOYMENT])
            return DeploymentConfig.model_validate(deployment_json)
        except Exception as e:
            logger.error("Failed to parse the message", exc_info=e)
            return None

    def handle(self, message: TargetedMqttMessage) -> None:
        logger.debug(
            f"Received app deployment request {message.payload.decode('utf-8')}"
        )
        content = self._filter(message)
        if content:
            logger.debug("Processing app download")
            for name, module in content.modules.items():
                logger.debug(f"parsing {name} {module.download_url}")
                download(str(module.download_url))
            body = {
                "deploymentId": content.deployment_id,
                "reconcileStatus": "ok",
            }
            response = {"deploymentStatus": json.dumps(body)}
            msg = MqttMessage(
                topic=MqttTopics.ATTRIBUTES.value, payload=json_bytes(response)
            )
            self._device.send_mqtt(msg)
            logger.debug("Finished app download")
