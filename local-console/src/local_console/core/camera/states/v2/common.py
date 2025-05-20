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

from local_console.core.camera.enums import MQTTTopics
from local_console.core.camera.schemas import PropertiesReport
from local_console.core.camera.states.base import BaseStateProperties
from local_console.core.camera.states.base import MQTTEvent
from local_console.core.camera.states.common import ConnectedCameraState
from local_console.core.camera.v2.components.device_info import AIModel
from local_console.core.camera.v2.components.device_states import DeviceStates
from local_console.core.camera.v2.components.network_settings import NetworkSettings
from local_console.core.camera.v2.components.private_deploy_firmware import (
    PrivateDeployFirmware,
)
from local_console.core.camera.v2.components.req_res_info import ReqInfo
from local_console.core.camera.v2.edge_system_common import DeviceInfo
from local_console.core.camera.v2.edge_system_common import EdgeSystemCommon
from local_console.core.commands.rpc_with_response import DirectCommandResponse
from local_console.core.commands.rpc_with_response import run_rpc_with_response
from local_console.core.config import Config
from local_console.core.helpers import merge_model_instances
from local_console.core.helpers import safe_get_next
from local_console.utils.random import random_id
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# MQTT constants
SYSINFO_TOPIC = "systemInfo"


class ConnectedCameraStateV2(ConnectedCameraState):

    # Due to the ability to set the reporting period, this can
    # be set to a much shorter connection timeout period.
    CONNECTION_STATUS_TIMEOUT = 20

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
            update = EdgeSystemCommon.model_validate(message.payload)
            self._refresh_from_report(update)

    def _refresh_from_report(self, report: EdgeSystemCommon) -> None:
        gathered = populate_properties(report)
        self.update_connection_configuration(report)
        merge_model_instances(self._state_properties.reported, gathered)
        self._state_properties.on_report_fn(self._id, self._state_properties.reported)

    async def _push_rpc(
        self,
        module_id: str,
        method: str,
        params: dict[str, Any],
        extra: dict[str, Any],
    ) -> DirectCommandResponse:
        # Not immediately returning the response here is an example of
        # how to implement an RPC call which would trigger a state transition,
        # being able to fetch the RPC response from the new state's enter()
        self._rpc_response = await run_rpc_with_response(
            self._mqtt._mqtt_port, module_id, method, params
        )
        return self._rpc_response

    async def send_configuration(
        self, module_id: str, property_name: str, data: dict[str, Any] | BaseModel
    ) -> None:
        serialized = (
            data.model_dump_json(exclude_none=True)
            if isinstance(data, BaseModel)
            else json.dumps(data)
        )
        message: dict = {f"configuration/{module_id}/{property_name}": serialized}
        payload = json.dumps(message)
        logger.debug(f"payload: {payload}")
        await self._mqtt.client.publish(MQTTTopics.ATTRIBUTES.value, payload=payload)

    async def run_command(
        self,
        module_id: str,
        method: str,
        params: dict[str, Any],
        extra: dict[str, Any],
    ) -> DirectCommandResponse:
        return await self._push_rpc(module_id, method, params, extra)

    def generate_req(self) -> ReqInfo:
        return ReqInfo(req_id=random_id())

    def update_connection_configuration(self, report: EdgeSystemCommon) -> None:
        """
        Updates the device MQTT and webserver connection configuration with the
        `endpoint_url` and `endpoint_port` provided in `state/$system/PRIVATE_endpoint_settings`.
        """
        config = Config().get_device_config(self._id)
        if report.private_endpoint_setting and (
            config.mqtt.host != report.private_endpoint_setting.endpoint_url
            or config.mqtt.port != report.private_endpoint_setting.endpoint_port
        ):
            config.mqtt.host = report.private_endpoint_setting.endpoint_url
            config.mqtt.port = report.private_endpoint_setting.endpoint_port
            Config().save_config()


def populate_properties(v2_report: EdgeSystemCommon) -> PropertiesReport:
    """
    Render the v2-specific properties report into the
    state's schema-agnostic properties report.
    """

    # Properties held in device_info
    cam_fw_version = None
    sensor_fw_version = None
    sensor_loader_version = None
    sensor_hardware = None
    dnn_versions = None
    match v2_report.device_info:
        case DeviceInfo(chips=chips_list):
            cam_fw_version = safe_get_next(
                (
                    info.firmware_version
                    for info in chips_list
                    if info.name == "main_chip"
                ),
                None,
            )
            sensor_fw_version = safe_get_next(
                (
                    info.firmware_version
                    for info in chips_list
                    if info.name == "sensor_chip"
                ),
                None,
            )
            sensor_loader_version = safe_get_next(
                (
                    info.loader_version
                    for info in chips_list
                    if info.name == "sensor_chip"
                ),
                None,
            )
            sensor_hardware = safe_get_next(
                (
                    info.hardware_version
                    for info in chips_list
                    if info.name == "sensor_chip"
                ),
                None,
            )

            ai_models = safe_get_next(
                (info.ai_models for info in chips_list if info.name == "sensor_chip"),
                None,
            )
            if ai_models is not None:
                ai_models = [
                    ai_model
                    for ai_model in ai_models
                    if ai_model != AIModel(version="", hash="", update_date="")
                ]
                dnn_versions = [mod.version for mod in ai_models]

    # Properties held in PRIVATE_deploy_firmware
    sensor_fw_ota_status = None
    cam_fw_ota_status = None
    match v2_report.private_deploy_firmware:
        case PrivateDeployFirmware(targets=target_list):
            sensor_fw_ota_status = safe_get_next(
                (
                    target.process_state
                    for target in target_list
                    if target.chip == "sensor_chip"
                ),
                None,
            )
            cam_fw_ota_status = safe_get_next(
                (
                    target.process_state
                    for target in target_list
                    if target.chip == "main_chip"
                ),
                None,
            )

    # Properties held in device_states
    cam_fw_status = None
    match v2_report.device_states:
        case DeviceStates() as ds:
            cam_fw_status = ds.process_state

    # Properties held in network_settings
    proxy_port = None
    proxy_user_name = None
    proxy_url = None
    ntp_url = None
    gateway_address = None
    subnet_mask = None
    ip_address = None
    dns_address = None
    match v2_report.network_settings:
        case NetworkSettings() as ns:
            proxy_port = ns.proxy_settings.proxy_port
            proxy_user_name = ns.proxy_settings.proxy_user_name
            proxy_url = ns.proxy_settings.proxy_url
            ntp_url = ns.ntp_url
            gateway_address = ns.static_settings_ipv4.gateway_address
            subnet_mask = ns.static_settings_ipv4.subnet_mask
            ip_address = ns.static_settings_ipv4.ip_address
            dns_address = ns.static_settings_ipv4.dns_address

    return PropertiesReport(
        cam_fw_version=cam_fw_version,
        sensor_fw_version=sensor_fw_version,
        sensor_fw_ota_status=sensor_fw_ota_status,
        cam_fw_ota_status=cam_fw_ota_status,
        sensor_loader_version=sensor_loader_version,
        sensor_hardware=sensor_hardware,
        sensor_status="",  # see note in PropertiesReport definition
        dnn_versions=dnn_versions,
        cam_fw_status=cam_fw_status,
        proxy_port=proxy_port,
        proxy_user_name=proxy_user_name,
        proxy_url=proxy_url,
        ntp_url=ntp_url,
        gateway_address=gateway_address,
        subnet_mask=subnet_mask,
        ip_address=ip_address,
        dns_address=dns_address,
        edge_app=v2_report.edge_app,
    )
