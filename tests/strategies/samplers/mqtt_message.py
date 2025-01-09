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
from typing import Any
from typing import Self

from local_console.core.camera.enums import MQTTTopics


class MockMQTTMessage:
    def __init__(self, topic: str, payload):
        self.topic = topic
        self.payload = payload

    @classmethod
    def config_status(
        cls,
        sensor_id: str = "100A509",
        dnn_model_version: list[str] = ["0308000000000100"],
        update_status: str = "Done",
    ) -> Self:
        data = {
            "Hardware": {
                "Sensor": "IMX500",
                "SensorId": "100A509",
                "KG": "1",
                "ApplicationProcessor": "3",
                "LedOn": True,
            },
            "Version": {
                "SensorFwVersion": "010707",
                "SensorLoaderVersion": "020301",
                "DnnModelVersion": ["0308000000000100"],
                "ApFwVersion": "X700F6",
                "ApLoaderVersion": "D10200",
            },
            "Status": {"Sensor": "Standby", "ApplicationProcessor": "Idle"},
            "OTA": {
                "SensorFwLastUpdatedDate": "",
                "SensorLoaderLastUpdatedDate": "",
                "DnnModelLastUpdatedDate": [""],
                "ApFwLastUpdatedDate": "",
                "UpdateProgress": 1,
                "UpdateStatus": "Done",
            },
            "Permission": {"FactoryReset": True},
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
        }

        data["Hardware"]["SensorId"] = sensor_id
        data["Version"]["DnnModelVersion"] = dnn_model_version
        data["OTA"]["UpdateStatus"] = update_status

        # Convert dictionary to JSON string
        json_str = json.dumps(data)

        # Encode JSON string to Base64
        base64_encoded = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
        payload = {"state/backdoor-EA_Main/placeholder": base64_encoded}
        topic = "v1/devices/me/attributes"
        return cls(topic, json.dumps(payload).encode("utf-8"))

    @classmethod
    def update_status(
        cls,
        deployment_id: str = "79a863e6ae6f55143a952705b11afbfeafbdb595d7c9ddc35f66cd48eeb46e5e",
        status: str = "ok",
        modules: dict[str, Any] | None = None,
    ) -> Self:
        topic = "v1/devices/me/attributes"
        body = {"deploymentId": deployment_id, "reconcileStatus": status}
        if modules:
            body["modules"] = modules
        payload = {"deploymentStatus": json.dumps(body)}
        return cls(topic, json.dumps(payload).encode("utf-8"))

    @classmethod
    def handshake_response(cls) -> Self:
        system_module: dict[str, Any] = {
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
                "UpdateStatus": "Done",
            },
            "Network": {
                "ProxyURL": "192.168.1.1",
                "ProxyPort": 1883,
                "ProxyUserName": "username_42",
                "IPAddress": "192.168.1.2",
                "SubnetMask": "255.255.255.0",
                "Gateway": "192.168.1.3",
                "DNS": "8.8.8.8",
                "NTP": "192.168.1.4",
            },
            "Permission": {"FactoryReset": True},
        }

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
                json.dumps(system_module).encode("utf-8")
            ).decode("utf-8"),
        }
        return cls(MQTTTopics.ATTRIBUTES.value, json.dumps(payload).encode("utf-8"))
