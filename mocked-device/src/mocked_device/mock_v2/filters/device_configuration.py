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
from typing import Annotated
from typing import Any

from mocked_device.message_base import MessageFilter
from mocked_device.mqtt.values import TargetedMqttMessage
from mocked_device.utils.topics import MqttTopics
from pydantic import AliasChoices
from pydantic import AliasPath
from pydantic import BaseModel
from pydantic import Field

logger = logging.getLogger(__name__)


class DesiredDeviceConfig(BaseModel):
    # May want to replace local_console.core.schemas.schemas.DesiredDeviceConfig with this:
    id: Annotated[
        str,
        Field(
            validation_alias=AliasChoices(
                "id", "configuration/$agent/configuration-id"
            ),
            serialization_alias="configuration/$agent/configuration-id",
        ),
    ] = ""
    report_status_interval_min: Annotated[
        int,
        Field(
            gt=0,
            validation_alias=AliasChoices(
                AliasPath("rs_interval", 0),
                "configuration/$agent/report-status-interval-max",
            ),
            serialization_alias="configuration/$agent/report-status-interval-max",
        ),
    ]
    report_status_interval_max: Annotated[
        int,
        Field(
            gt=0,
            validation_alias=AliasChoices(
                AliasPath("rs_interval", 1),
                "configuration/$agent/report-status-interval-min",
            ),
            serialization_alias="configuration/$agent/report-status-interval-min",
        ),
    ]
    registry_auth: Annotated[
        dict[str, Any],
        Field(
            validation_alias=AliasChoices(
                "registry_auth", "configuration/$agent/registry-auth"
            ),
            serialization_alias="configuration/$agent/registry-auth",
        ),
    ] = {}


class InnerDeviceConfigurationMessage(BaseModel):
    desiredDeviceConfig: DesiredDeviceConfig


class DeviceConfigurationMessage(BaseModel):
    desiredDeviceConfig: InnerDeviceConfigurationMessage


class DeviceConfigurationFilterV2(MessageFilter):
    def topic(self) -> str:
        return MqttTopics.ATTRIBUTES.value

    def filter(self, message: TargetedMqttMessage) -> DesiredDeviceConfig | None:
        try:
            conf = DeviceConfigurationMessage.model_validate_json(message.payload)
            return conf.desiredDeviceConfig.desiredDeviceConfig
        except Exception:
            return None
