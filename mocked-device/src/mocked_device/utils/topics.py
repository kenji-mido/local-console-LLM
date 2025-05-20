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
from enum import Enum


class MqttTopics(Enum):
    ATTRIBUTES = "v1/devices/me/attributes"
    ATTRIBUTES_REQ = "v1/devices/me/attributes/request"
    RPC_REQ = "v1/devices/me/rpc/request"
    RPC_RESP = "v1/devices/me/rpc/response"
    TELEMETRY = "v1/devices/me/telemetry"

    def suffixed(self, suffix: str) -> str:
        return f"{self.value}/{suffix}"

    def generic(self) -> str:
        return self.suffixed("+")

    def suffix_from(self, topic: str) -> str | None:
        if topic.startswith(self.value):
            return topic[len(self.value) + 1 :]
        return None
