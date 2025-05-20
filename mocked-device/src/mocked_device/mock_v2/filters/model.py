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

from mocked_device.message_base import MessageFilter
from mocked_device.mock_v2.ai_model_message import DeployAiModel
from mocked_device.mqtt.values import TargetedMqttMessage
from mocked_device.utils.topics import MqttTopics


logger = logging.getLogger(__name__)

DEPLOYMENT_AI_MODEL_ENTRY = "configuration/$system/PRIVATE_deploy_ai_model"


class ModelFilterV2(MessageFilter[DeployAiModel]):

    def topic(self) -> str:
        return MqttTopics.ATTRIBUTES.value

    def filter(self, message: TargetedMqttMessage) -> None | DeployAiModel:
        payload = json.loads(message.payload)
        if message.topic != self.topic() or DEPLOYMENT_AI_MODEL_ENTRY not in payload:
            return None

        return DeployAiModel(**json.loads(payload[DEPLOYMENT_AI_MODEL_ENTRY]))
