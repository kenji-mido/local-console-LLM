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
from enum import StrEnum
from typing import Any

from mocked_device.message_base import MessageBuilder
from mocked_device.mqtt.values import MqttMessage
from mocked_device.utils.json import json_bytes
from mocked_device.utils.topics import MqttTopics
from pydantic import BaseModel


class OTAUpdateStatus(StrEnum):
    DOWNLOADING = "Downloading"
    UPDATING = "Updating"
    REBOOTING = "Rebooting"
    DONE = "Done"
    FAILED = "Failed"


class HardwareFields(BaseModel):
    Sensor: str = "IMX500"
    SensorId: str = "100A50500A2012062364012000000000"
    KG: str = "1"
    ApplicationProcessor: str = ""
    LedOn: bool = True


class VersionFields(BaseModel):
    SensorFwVersion: str = "020000"
    SensorLoaderVersion: str = "020301"
    DnnModelVersion: list[Any] = []
    ApFwVersion: str = "D52408"
    ApLoaderVersion: str = "D10300"


class StatusFields(BaseModel):
    Sensor: str = "Standby"
    ApplicationProcessor: str = "Idle"


class OTAFields(BaseModel):
    SensorFwLastUpdatedDate: str = "20241009084026"
    SensorLoaderLastUpdatedDate: str = ""
    DnnModelLastUpdatedDate: list[Any] = []
    ApFwLastUpdatedDate: str = ""
    UpdateProgress: int = 100
    UpdateStatus: OTAUpdateStatus = OTAUpdateStatus.DONE


class NetworkFields(BaseModel):
    ProxyURL: str = "localhost"
    ProxyPort: int = 1883
    ProxyUserName: str = "username_42"
    IPAddress: str = "localhost"
    SubnetMask: str = ""
    Gateway: str = ""
    DNS: str = ""
    NTP: str = "pool.ntp.org"


class PermissionFields(BaseModel):
    FactoryReset: bool = True


class DeploymentStatus(BaseModel, MessageBuilder):
    Hardware: HardwareFields = HardwareFields()
    Version: VersionFields = VersionFields()
    Status: StatusFields = StatusFields()
    OTA: OTAFields = OTAFields()
    Network: NetworkFields = NetworkFields()
    Permission: PermissionFields = PermissionFields()

    def build(self) -> MqttMessage:
        payload = {
            "deploymentStatus": '{"instances":{"backdoor-EA_Main":{"status":"unknown"},"backdoor-EA_UD":{"status":"unknown"}},"modules":{}}',
            "systemInfo": {
                "utsname": {
                    "sysname": "NuttX",
                    "nodename": "",
                    "release": "0.0.0",
                    "version": "d578a84c Apr 29 2024 10:00:56",
                    "machine": "xtensa",
                }
            },
            "state/backdoor-EA_Main/placeholder": base64.b64encode(
                json_bytes(self.model_dump())
            ).decode("utf-8"),
        }
        return MqttMessage(
            topic=MqttTopics.ATTRIBUTES.value,
            payload=json_bytes(payload),
        )


class EventLog(BaseModel, MessageBuilder):
    DeviceID: str = "Aid-80070001-0000-2000-9002-0000000001fe"
    Level: str = "Warn"
    Time: str = "20250204172549"
    Component: int = 2
    ErrorCode: int = 1
    Description: str = ""

    def build(self) -> MqttMessage:
        payload = {
            "ts": 1738689949831,
            "values": {"backdoor-EA_Main/EventLog": self.model_dump()},
        }
        return MqttMessage(
            topic=MqttTopics.TELEMETRY.value,
            payload=json_bytes(payload),
        )
