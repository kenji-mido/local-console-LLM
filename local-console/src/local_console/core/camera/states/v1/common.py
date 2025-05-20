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
from base64 import b64decode
from base64 import b64encode
from typing import Any
from typing import TypeVar

from local_console.core.camera.enums import MQTTTopics
from local_console.core.camera.schemas import PropertiesReport
from local_console.core.camera.states.base import BaseStateProperties
from local_console.core.camera.states.base import MQTTEvent
from local_console.core.camera.states.common import ConnectedCameraState
from local_console.core.camera.states.v1.rpc import DirectCommandResponse
from local_console.core.camera.states.v1.rpc import run_rpc_with_response
from local_console.core.helpers import publish_configure
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.core.schemas.edge_cloud_if_v1 import Permission
from local_console.core.schemas.edge_cloud_if_v1 import SetFactoryReset
from local_console.core.schemas.schemas import OnWireProtocol

logger = logging.getLogger(__name__)


# MQTT constants
EA_STATE_TOPIC = "state/backdoor-EA_Main/placeholder"
SYSINFO_TOPIC = "systemInfo"


class ConnectedCameraStateV1(ConnectedCameraState):

    def __init__(self, base: BaseStateProperties) -> None:
        super().__init__(base)

        # The necessity for the RPC response variable stems from the product
        # choice to use API-exposed raw RPCs as the only way to trigger
        # commonly used actions such as image streaming. Such state
        # transition-triggering RPCs yield responses from the target camera
        # which are expected to be relayed to the originating API call for
        # its response to the API caller.
        self._rpc_response: DirectCommandResponse | None = None

    async def on_message_received(self, message: MQTTEvent) -> None:
        await super().on_message_received(message)

        if message.topic == MQTTTopics.ATTRIBUTES.value:
            if EA_STATE_TOPIC in message.payload:
                await self._process_state_topic(message.payload)

    async def _process_state_topic(self, payload: dict[str, Any]) -> None:
        try:
            decoded = json.loads(b64decode(payload[EA_STATE_TOPIC]))
        except UnicodeDecodeError:
            decoded = json.loads(payload[EA_STATE_TOPIC])

        device_report = DeviceConfiguration.model_validate(decoded)
        self._refresh_from_report(device_report)
        await self._process_factory_reset(device_report)

    async def _process_factory_reset(self, report: DeviceConfiguration) -> None:
        factory_reset = report.Permission.FactoryReset
        logger.debug(f"Factory Reset is {factory_reset}")
        if not factory_reset:
            await publish_configure(
                self._mqtt.client,
                OnWireProtocol.EVP1,
                "backdoor-EA_Main",
                "placeholder",
                SetFactoryReset(
                    Permission=Permission(FactoryReset=True)
                ).model_dump_json(),
            )

    def _refresh_from_report(self, report: DeviceConfiguration) -> None:
        new_report = populate_properties(report)
        self._state_properties.reported = new_report
        self._state_properties.on_report_fn(self._id, new_report)

    async def _push_rpc(
        self,
        module_id: str,
        method: str,
        params: dict[str, Any],
        extra: dict[str, Any],
    ) -> DirectCommandResponse | None:
        # Not immediately returning the response here is an example of
        # how to implement an RPC call which would trigger a state transition,
        # being able to fetch the RPC response from the new state's enter()
        self._rpc_response = await run_rpc_with_response(
            self._mqtt._mqtt_port, module_id, method, params
        )
        return self._rpc_response

    async def _rpc_stop_streaming(self) -> None:
        await self._push_rpc("backdoor-EA_Main", "StopUploadInferenceData", {}, {})

    async def send_configuration(
        self, module_id: str, property_name: str, data: dict[str, Any]
    ) -> None:
        serialized = json.dumps(data)
        config = b64encode(serialized.encode("utf-8")).decode("utf-8")

        if module_id == "$system":
            module_id = "backdoor-EA_Main"

        message: dict = {f"configuration/{module_id}/{property_name}": config}
        payload = json.dumps(message)
        logger.debug(f"payload: {payload}")
        await self._mqtt.client.publish(MQTTTopics.ATTRIBUTES.value, payload=payload)


def populate_properties(v1_report: DeviceConfiguration) -> PropertiesReport:
    """
    Render the v1-specific properties report into the
    state's schema-agnostic properties report.
    """

    T = TypeVar("T")

    def _pluck_from_network(attr: str, default: T) -> T:
        if v1_report.Network:
            return getattr(v1_report.Network, attr, default)
        else:
            return default

    return PropertiesReport(
        cam_fw_version=v1_report.Version.ApFwVersion,
        cam_fw_ota_status=v1_report.OTA.UpdateStatus,
        sensor_fw_version=v1_report.Version.SensorFwVersion,
        sensor_fw_ota_status=v1_report.OTA.UpdateStatus,
        sensor_loader_version=v1_report.Version.SensorLoaderVersion or "",
        sensor_hardware=v1_report.Hardware.Sensor,
        sensor_status=v1_report.Status.Sensor,
        dnn_versions=v1_report.Version.DnnModelVersion.root,
        cam_fw_status=v1_report.Status.ApplicationProcessor,
        proxy_port=_pluck_from_network("ProxyPort", 0),
        proxy_user_name=_pluck_from_network("ProxyUserName", ""),
        proxy_url=_pluck_from_network("ProxyURL", ""),
        ntp_url=_pluck_from_network("NTP", ""),
        gateway_address=_pluck_from_network("Gateway", ""),
        subnet_mask=_pluck_from_network("SubnetMask", ""),
        ip_address=_pluck_from_network("IPAddress", ""),
        dns_address=_pluck_from_network("DNS", ""),
    )
