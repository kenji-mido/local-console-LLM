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
from mocked_device.mock_v2.ea_config import APP_CONFIG_KEY
from mocked_device.mock_v2.ea_config import EdgeAppSpec
from mocked_device.mqtt.values import TargetedMqttMessage
from mocked_device.utils.topics import MqttTopics

logger = logging.getLogger(__name__)

CONF_KEY = f"configuration/node/{APP_CONFIG_KEY}"


class AppConfigurationFilterV2(MessageFilter):

    def topic(self) -> str:
        return MqttTopics.ATTRIBUTES.value

    def filter(self, message: TargetedMqttMessage) -> EdgeAppSpec | None:
        try:
            body = json.loads(message.payload)
            config_str = body.get(CONF_KEY)
            if config_str:
                return EdgeAppSpec.model_validate_json(config_str)
        except Exception:
            pass

        return None
