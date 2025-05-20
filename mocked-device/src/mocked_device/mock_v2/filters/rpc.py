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
from typing import Any

from mocked_device.message_base import MessageFilter
from mocked_device.mqtt.values import TargetedMqttMessage
from mocked_device.utils.topics import MqttTopics
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DirectCommandRequest(BaseModel):
    reqid: str
    method: str
    instance: str
    params: str  # JSON string that needs parsing


class RPCCommandV2(BaseModel):
    method: str
    params: dict[str, DirectCommandRequest]


class RPCFilterV2(MessageFilter[RPCCommandV2]):
    def topic(self) -> str:
        return MqttTopics.RPC_REQ.generic()

    def _parse(self, payload: bytes) -> Any:
        try:
            return json.loads(payload)
        except Exception as e:
            logger.error(f"Received invalid JSON payload: {payload!r}", exc_info=e)
            return None

    def filter(self, message: TargetedMqttMessage) -> RPCCommandV2 | None:
        message_id = MqttTopics.RPC_REQ.suffix_from(message.topic)
        if not message_id:
            return None
        content = self._parse(message.payload)
        if not content:
            return None
        logger.debug(f"RPC method: {content.get('method')}")
        if "params" not in content or "direct-command-request" not in content["params"]:
            logger.error("Missing direct-command-request in params")
            return None

        return RPCCommandV2(method=content["method"], params=content["params"])
