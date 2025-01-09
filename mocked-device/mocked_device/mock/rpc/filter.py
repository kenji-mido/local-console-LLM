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

from mocked_device.mock.base import MessageFilter
from mocked_device.mock.topics import MqttTopics
from mocked_device.mqtt.values import TargetedMqttMessage
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class RPCCommand(BaseModel):
    message_id: str
    method: str
    instance: str
    params: dict[str, Any]


class RPCFilter(MessageFilter[RPCCommand]):
    def topic(self) -> str:
        return MqttTopics.RPC_REQ.generic()

    def _parse(self, payload: bytes) -> dict[str, Any] | None:
        try:
            return json.loads(payload)  # type: ignore[no-any-return]
        except Exception as e:
            logger.error(f"We get a payload that is not a json {payload!r}", exc_info=e)
            return None

    def filter(self, message: TargetedMqttMessage) -> RPCCommand | None:
        message_id = MqttTopics.RPC_REQ.suffix_from(message.topic)
        if not message_id:
            return None
        content = self._parse(message.payload)
        if not content:
            return None
        if "method" not in content or content["method"] != "ModuleMethodCall":
            return None
        if "params" not in content:
            logger.error("We did receive a ModuleMethodCall without params")
            return None
        if "moduleMethod" not in content["params"]:
            logger.error("We did receive a ModuleMethodCall without method")
            return None
        if "moduleInstance" not in content["params"]:
            logger.error("We did receive a ModuleMethodCall without instance")
            return None
        if "params" not in content["params"]:
            logger.error("We did receive a ModuleMethodCall without sub-params")
            return None
        return RPCCommand(
            message_id=message_id,
            method=content["params"]["moduleMethod"],
            instance=content["params"]["moduleInstance"],
            params=content["params"]["params"],
        )
