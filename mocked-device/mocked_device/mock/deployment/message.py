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
from typing import Any

from mocked_device.mock.base import MessageBuilder
from mocked_device.mock.topics import MqttTopics
from mocked_device.mqtt.values import MqttMessage
from mocked_device.utils.json import json_bytes


class DeploymentStatusBuilder(MessageBuilder):
    def __init__(
        self, dnn_model_version: list[str] = [], ota_update_status: str = "Done"
    ):
        self.dnn_model_version = dnn_model_version
        self.ota_update_status = ota_update_status

    def _system_module(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "Hardware": {
                "Sensor": "IMX500",
                "SensorId": "100A50500A2012062364012000000000",
                "KG": "1",
                "ApplicationProcessor": "",
                "LedOn": True,
            },
            "Version": {
                "SensorFwVersion": "020000",
                "SensorLoaderVersion": "020301",
                "DnnModelVersion": [],
                "ApFwVersion": "D52408",
                "ApLoaderVersion": "D10300",
            },
            "Status": {"Sensor": "Standby", "ApplicationProcessor": "Idle"},
            "OTA": {
                "SensorFwLastUpdatedDate": "20241009084026",
                "SensorLoaderLastUpdatedDate": "",
                "DnnModelLastUpdatedDate": [],
                "ApFwLastUpdatedDate": "",
                "UpdateProgress": 100,
                "UpdateStatus": self.ota_update_status,
            },
            "Network": {
                "ProxyURL": "localhost",
                "ProxyPort": 1883,
                "ProxyUserName": "username_42",
                "IPAddress": "localhost",
                "SubnetMask": "",
                "Gateway": "",
                "DNS": "",
                "NTP": "",
            },
            "Permission": {"FactoryReset": True},
        }
        payload["Version"]["DnnModelVersion"] = self.dnn_model_version
        return payload

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
                json_bytes(self._system_module())
            ).decode("utf-8"),
        }
        return MqttMessage(
            topic=MqttTopics.ATTRIBUTES.value,
            payload=json_bytes(payload),
        )
