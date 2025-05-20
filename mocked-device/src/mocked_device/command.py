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
from enum import Enum
from typing import Any
from typing import Literal

from mocked_device.mqtt.values import TargetedMqttMessage
from mocked_device.utils.json import get_field
from pydantic import BaseModel
from pydantic import Field

MODULE = "configuration/backdoor-EA_Main/placeholder"

logger = logging.getLogger(__name__)

DELETE_ATT: Literal["DeleteNetworkID"] = "DeleteNetworkID"


class OTAType(Enum):
    DNN = "DnnModel"
    SENSORFW = "SensorFw"
    APPFW = "ApFw"


class BaseOTA(BaseModel):
    type: OTAType = Field(alias="UpdateModule")


class Delete(BaseOTA):
    network_id: str = Field(alias=DELETE_ATT)


class Package(BaseOTA):
    url: str = Field(alias="PackageUri")
    version: str = Field(alias="DesiredVersion")
    hash: str = Field(alias="HashValue")


def __filter_OTA(message: TargetedMqttMessage) -> None | dict[str, Any]:
    json_payload = json.loads(message.payload)
    if MODULE not in json_payload:
        return None
    content = base64.b64decode(
        json_payload["configuration/backdoor-EA_Main/placeholder"]
    ).decode("utf-8")
    json_content = json.loads(content)
    return {MODULE: json_content}


def __parse_delete_or_package(
    ota_raw: dict[str, Any] | str | None
) -> None | Delete | Package:
    if not isinstance(ota_raw, dict):
        logger.info(f"Unexpected ota input {ota_raw}")
        return None
    if DELETE_ATT in ota_raw:
        return Delete.model_validate(ota_raw)
    return Package.model_validate(ota_raw)


def filter(message: TargetedMqttMessage) -> None | Delete | Package:
    payload = __filter_OTA(message)
    if payload is None:
        return None
    ota_raw = get_field(payload, f"{MODULE}.OTA")
    if ota_raw is None:
        logger.debug("Configuration command that is not OTA")
    return __parse_delete_or_package(ota_raw)
