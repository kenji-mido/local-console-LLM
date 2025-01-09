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
from datetime import datetime

import pytest
from local_console.core.camera.mixin_mqtt import MQTTEvent
from local_console.core.camera.mixin_mqtt import MQTTMixin
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.core.schemas.schemas import OnWireProtocol

from tests.fixtures.agent import mocked_agent
from tests.strategies.samplers.mqtt_message import MockMQTTMessage


@pytest.mark.trio
async def test_listen_to_rpc_responses() -> None:
    with mocked_agent() as mock_agent:

        topic = "v1/devices/me/rpc/response/1"
        payload = {
            "moduleInstance": "backdoor-EA_Main",
            "status": 0,
            "response": {"Result": "Succeeded", "Image": "BASE64IMAGE"},
        }

        msg = MockMQTTMessage(topic, json.dumps(payload).encode("utf-8"))
        mock_agent.send_messages([msg])
        mixin_mqtt = MQTTMixin()
        mixin_mqtt.mqtt_host.value = "host"
        mixin_mqtt.mqtt_port.value = 1883
        mixin_mqtt._onwire_schema = OnWireProtocol.EVP1
        observer_called = False

        def observer(new_event: MQTTEvent, _: MQTTEvent) -> None:
            nonlocal observer_called
            assert new_event.topic == topic
            assert new_event.payload == payload
            observer_called = True

        mixin_mqtt.rpc_response.subscribe(observer)

        send = datetime.now()
        await mixin_mqtt.mqtt_setup()

        assert observer_called
        assert mixin_mqtt._last_reception
        assert send < mixin_mqtt._last_reception


@pytest.mark.trio
async def test_process_incomplete_message() -> None:

    with mocked_agent() as mock_agent:

        topic = "v1/devices/me/attributes"
        payload = {
            "deploymentStatus": '{"instances":{"backdoor-EA_Main":{"status":"unknown"},"backdoor-EA_UD":{"status":"unknown"}},"modules":{}}',
            "systemInfo": {
                "utsname": {
                    "sysname": "NuttX",
                    "nodename": "",
                    "release": "0.0.0",
                    "version": "d578a84c Apr 10 2024 05:17:33",
                    "machine": "xtensa",
                }
            },
            "state/backdoor-EA_Main/placeholder": "eyJIYXJkd2FyZSI6eyJTZW5zb3IiOiIiLCJTZW5zb3JJZCI6IiIsIktHIjoiIiwiQXBwbGljYXRpb25Qcm9jZXNzb3IiOiIiLCJMZWRPbiI6dHJ1ZX0sIlZlcnNpb24iOnsiU2Vuc29yRndWZXJzaW9uIjoiMDEwNzA3IiwiU2Vuc29yTG9hZGVyVmVyc2lvbiI6IjAyMDMwMSIsIkRubk1vZGVsVmVyc2lvbiI6W10sIkFwRndWZXJzaW9uIjoiWDcwMEY2IiwiQ2FtZXJhU2V0dXBGaWxlVmVyc2lvbiI6eyJDb2xvck1hdHJpeFN0ZCI6IiIsIkNvbG9yTWF0cml4Q3VzdG9tIjoiIiwiR2FtbWFTdGQiOiIiLCJHYW1tYUN1c3RvbSI6IiIsIkxTQ0lTUFN0ZCI6IiIsIkxTQ0lTUEN1c3RvbSI6IiIsIkxTQ1Jhd1N0ZCI6IiIsIkxTQ1Jhd0N1c3RvbSI6IiIsIlByZVdCU3RkIjoiIiwiUHJlV0JDdXN0b20iOiIiLCJEZXdhcnBTdGQiOiIiLCJEZXdhcnBDdXN0b20iOiIifX0sIlN0YXR1cyI6eyJTZW5zb3IiOiJFcnJvciIsIkFwcGxpY2F0aW9uUHJvY2Vzc29yIjoiSWRsZSIsIlNlbnNvclRlbXBlcmF0dXJlIjo1MX0sIk9UQSI6eyJTZW5zb3JGd0xhc3RVcGRhdGVkRGF0ZSI6IiIsIlNlbnNvckxvYWRlckxhc3RVcGRhdGVkRGF0ZSI6IiIsIkRubk1vZGVsTGFzdFVwZGF0ZWREYXRlIjpbXSwiQXBGd0xhc3RVcGRhdGVkRGF0ZSI6IiIsIlVwZGF0ZVByb2dyZXNzIjoxMDAsIlVwZGF0ZVN0YXR1cyI6IkRvbmUifSwiSW1hZ2UiOnsiRnJhbWVSYXRlIjowLCJEcml2ZU1vZGUiOjB9LCJFeHBvc3VyZSI6eyJFeHBvc3VyZU1vZGUiOiJhdXRvIiwiRXhwb3N1cmVNYXhFeHBvc3VyZVRpbWUiOjIwLCJFeHBvc3VyZU1pbkV4cG9zdXJlVGltZSI6MzMsIkV4cG9zdXJlTWF4R2FpbiI6MjQsIkFFU3BlZWQiOjMsIkV4cG9zdXJlQ29tcGVuc2F0aW9uIjo2LCJFeHBvc3VyZVRpbWUiOjE4LCJFeHBvc3VyZUdhaW4iOjEsIkZsaWNrZXJSZWR1Y3Rpb24iOjd9LCJXaGl0ZUJhbGFuY2UiOnsiV2hpdGVCYWxhbmNlTW9kZSI6ImF1dG8iLCJXaGl0ZUJhbGFuY2VQcmVzZXQiOjAsIldoaXRlQmFsYW5jZVNwZWVkIjozfSwiQWRqdXN0bWVudCI6eyJDb2xvck1hdHJpeCI6InN0ZCIsIkdhbW1hIjoic3RkIiwiTFNDLUlTUCI6InN0ZCIsIkxTQy1SYXciOiJzdGQiLCJQcmVXQiI6InN0ZCIsIkRld2FycCI6Im9mZiJ9LCJSb3RhdGlvbiI6eyJSb3RBbmdsZSI6MH0sIkRpcmVjdGlvbiI6eyJWZXJ0aWNhbCI6Ik5vcm1hbCIsIkhvcml6b250YWwiOiJOb3JtYWwifSwiTmV0d29yayI6eyJQcm94eVVSTCI6IiIsIlByb3h5UG9ydCI6MCwiUHJveHlVc2VyTmFtZSI6IiIsIklQQWRkcmVzcyI6IiIsIlN1Ym5ldE1hc2siOiIiLCJHYXRld2F5IjoiIiwiRE5TIjoiIiwiTlRQIjoicG9vbC5udHAub3JnIn0sIlBlcm1pc3Npb24iOnsiRmFjdG9yeVJlc2V0Ijp0cnVlfX0=",
        }

        msg = MockMQTTMessage(topic, json.dumps(payload).encode("utf-8"))
        mock_agent.send_messages([msg])
        mixin_mqtt = MQTTMixin()
        mixin_mqtt.mqtt_host.value = "host"
        mixin_mqtt.mqtt_port.value = 1883
        mixin_mqtt._onwire_schema = OnWireProtocol.EVP1

        await mixin_mqtt.mqtt_setup()

        assert mixin_mqtt.device_config.value
        assert isinstance(mixin_mqtt.device_config.value, DeviceConfiguration)
        assert mixin_mqtt.device_config.value.Version.ApFwVersion == "X700F6"
