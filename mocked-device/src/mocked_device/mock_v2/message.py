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
from enum import StrEnum
from typing import Optional

from mocked_device.message_base import MessageBuilder
from mocked_device.mock_v2.ai_model_message import DeployAiModel
from mocked_device.mock_v2.ea_config import EdgeAppSpec
from mocked_device.mock_v2.ea_config import ReqInfo
from mocked_device.mock_v2.ea_config import ResInfo
from mocked_device.mock_v2.ea_config import ResponseCode
from mocked_device.mqtt.values import MqttMessage
from mocked_device.utils.json import json_bytes
from mocked_device.utils.topics import MqttTopics
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class AiModel(BaseModel):
    version: str = ""
    hash: str = ""
    update_date: str = ""


class Chip(BaseModel):
    name: str = ""
    id: str = ""
    hardware_version: str = ""
    temperature: int = 0
    loader_version: str = "010300"
    loader_hash: str = ""
    update_date_loader: str = ""
    firmware_version: str = "0.9.3"
    firmware_hash: str = ""
    update_date_firmware: str = ""
    ai_models: list[AiModel] = []


class MainChip(Chip):
    name: str = "main_chip"


class SensorChip(Chip):
    name: str = "sensor_chip"
    id: str = "00000000000000000000000000000000"
    hardware_version: str = "ffff"
    temperature: int = 35
    loader_version: str = "0"
    update_date_loader: str = "1970-01-01T00:00:06.000Z"
    firmware_version: str = "900000"
    update_date_firmware: str = "1970-01-01T00:00:06.000Z"
    ai_models: list[AiModel] = [AiModel(), AiModel(), AiModel(), AiModel()]


class DeviceInfo(BaseModel):
    device_manifest: str = (
        "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJBSVRSSU9TQ2VydFVVSUQiOiJBaWQtMDAwMTAwMDEtMDAwMC0yMDAwLTkwMDItMDAwMDAwMDAwMWQxIiwiaWF0IjoxNzQ3MzA4MDMxfQ.xGa42ZKJQ3G3R4o5K0PBAnT4rUfntwfGFO_HJY0RHgher2aApTX_pmHoyNOkaVXAmuTDWZIAGN4ENIpvMs9seA"
    )
    chips: list[Chip] = [MainChip(), SensorChip()]


class Source(BaseModel):
    type: int = 0
    level: int = 100


class PowerStates(BaseModel):
    source: list[Source] = [Source()]
    in_use: int = 0
    is_battery_low: bool = False


class MachineState(StrEnum):
    IDLE = "Idle"
    EMERGENCY_STOP = "EmergencyStop"
    POWER_SAVING = "PowerSaving"


class DeviceState(BaseModel):
    power_states: PowerStates = PowerStates()
    process_state: MachineState = MachineState.IDLE
    hours_meter: int = 8
    bootup_reason: int = 0
    last_bootup_time: str = "2025-03-05T17:19:05.103Z"


class LogSetting(BaseModel):
    filter: str = ""
    level: int = 3
    destination: int = 0
    storage_name: str = ""
    path: str = ""


class SystemSetting(BaseModel):
    req_info: ReqInfo = ReqInfo(req_id="")
    led_enabled: bool = True
    temperature_update_interval: int = 10
    log_settings: list[LogSetting] = [
        LogSetting(filter="main"),
        LogSetting(filter="sensor"),
        LogSetting(filter="companion_fw"),
        LogSetting(filter="companion_app"),
    ]
    res_info: ResInfo = ResInfo(res_id="", code=ResponseCode.OK, detail_msg="")


class NetworkSetting(BaseModel):
    req_info: ReqInfo = ReqInfo(req_id="")
    ip_method: int = 0
    ntp_url: str = "pool.ntp.org"
    static_settings_ipv6: dict[str, str] = {
        "ip_address": "",
        "subnet_mask": "",
        "gateway_address": "",
        "dns_address": "",
    }
    static_settings_ipv4: dict[str, str] = {
        "ip_address": "",
        "subnet_mask": "",
        "gateway_address": "",
        "dns_address": "",
    }
    proxy_settings: dict[str, str | int] = {
        "proxy_url": "",
        "proxy_port": 0,
        "proxy_user_name": "",
        "proxy_password": "",
    }
    res_info: ResInfo = ResInfo(res_id="", code=ResponseCode.OK, detail_msg="")


class PrivateEndpointSetting(BaseModel):
    req_info: ReqInfo = ReqInfo(req_id="")
    endpoint_url: str = "localhost"
    endpoint_port: int = 1883
    protocol_version: str = "TB"
    res_info: ResInfo = ResInfo(res_id="", code=ResponseCode.OK, detail_msg="")


class WirelessSetting(BaseModel):
    req_info: ReqInfo = ReqInfo(req_id="")
    sta_mode_setting: dict[str, str | int] = {
        "ssid": "",
        "password": "",
        "encryption": 0,
    }
    res_info: ResInfo = ResInfo(res_id="", code=ResponseCode.OK, detail_msg="")


class IntervalSettings(BaseModel):
    base_time: str = "00.00"
    capture_interval: int = 120
    config_interval: int = 240


class PeriodicSetting(BaseModel):
    req_info: ReqInfo = ReqInfo(req_id="")
    operation_mode: int = 0
    recovery_method: int = 0
    interval_settings: list[IntervalSettings] = [IntervalSettings(), IntervalSettings()]
    ip_addr_setting: str = "dhcp"
    res_info: ResInfo = ResInfo(res_id="", code=ResponseCode.OK, detail_msg="")


class EdgeAppStatus(BaseModel):
    deployed: bool = False
    spec: EdgeAppSpec = EdgeAppSpec()


class ReportStatusV2(BaseModel, MessageBuilder):
    first_send: bool = False
    system_device_info: DeviceInfo = DeviceInfo()
    system_device_states: DeviceState = DeviceState()
    system_system_settings: SystemSetting = SystemSetting()
    system_device_capabilities: dict[str, bool | int] = {
        "is_battery_supported": False,
        "supported_wireless_mode": 3,
        "is_periodic_supported": False,
        "is_sensor_postprocess_supported": True,
    }
    system_network_settings: NetworkSetting = NetworkSetting()
    system_private_reserved: dict[str, str] = {
        "schema": "dtmi:com:sony_semicon:aitrios:sss:edge:system:t3p;2"
    }
    system_private_endpoint_settings: PrivateEndpointSetting = PrivateEndpointSetting()
    system_wireless_setting: WirelessSetting = WirelessSetting()
    system_periodic_setting: PeriodicSetting = PeriodicSetting()
    system_ai_model_deployment: DeployAiModel = DeployAiModel()
    single_app_status: EdgeAppStatus = EdgeAppStatus()

    def build(self) -> MqttMessage:
        payload = {
            "state/$system/device_info": self.system_device_info.model_dump_json(),
            "state/$system/device_states": self.system_device_states.model_dump_json(),
            "state/$system/system_settings": self.system_system_settings.model_dump_json(),
            "state/$system/device_capabilities": json.dumps(
                self.system_device_capabilities
            ),
            "state/$system/PRIVATE_reserved": json.dumps(self.system_private_reserved),
            "state/$system/network_settings": self.system_network_settings.model_dump_json(),
        }

        if self.first_send:
            payload.update(
                {
                    "state/$system/PRIVATE_endpoint_settings": self.system_private_endpoint_settings.model_dump_json(),
                    "state/$system/wireless_setting": self.system_wireless_setting.model_dump_json(),
                    "state/$system/periodic_setting": self.system_periodic_setting.model_dump_json(),
                }
            )

        if self.system_ai_model_deployment.req_info.req_id:
            payload.update(
                {
                    "state/$system/PRIVATE_deploy_ai_model": self.system_ai_model_deployment.model_dump_json(),
                }
            )

        # If there is a deployed app
        if self.single_app_status.deployed:
            payload.update(
                {
                    "state/node/edge_app": self.single_app_status.spec.model_dump_json(
                        exclude_none=True
                    )
                }
            )

        self.first_send = True
        return MqttMessage(
            topic=MqttTopics.ATTRIBUTES.value,
            payload=json_bytes(payload),
        )


# Define the model for event_log with default values
class EventLog(BaseModel):
    serial: str = "Aid-00010001-0000-2000-9002-0000000001d1"
    level: int = 3
    timestamp: str = "1970-01-01T00:00:00.460Z"
    component_id: int = 1048576
    event_id: int = 34048


class EventLogV2(BaseModel, MessageBuilder):

    system_event_log: EventLog = EventLog()

    def build(self) -> MqttMessage:
        payload = {"$system/event_log": self.system_event_log.model_dump()}

        return MqttMessage(
            topic=MqttTopics.TELEMETRY.value,
            payload=json_bytes(payload),
        )


class SystemInfo(BaseModel):
    os: str = "NuttX"
    arch: str = "xtensa"
    evp_agent: str = "v1.40.0"
    evp_agent_commit_hash: str = "19ba152d5ad174999ac3a0e669eece54b312e5d1"
    wasmMicroRuntime: str = "v2.1.0"
    protocolVersion: str = "EVP2-TB"


class InstanceStatus(StrEnum):
    OK = "ok"
    ERROR = "error"
    STARTING = "starting"
    STARTED = "started"
    UNKNOWN = "unknown"
    STOPPING = "stopping"
    SELF_EXITING = "self-exiting"
    STATUS_CHECK_BACKOFF = "status-check-backoff"


class ReconcileStatus(StrEnum):
    APPLYING = "applying"
    OK = "ok"
    ERROR = "error"


class ModuleStatus(StrEnum):
    DOWNLOADING = "downloading"
    UNKNOWN = "unknown"
    ERROR = "error"
    OK = "ok"


class Instance(BaseModel):
    status: str
    moduleId: str


class Module(BaseModel):
    status: ModuleStatus
    failureMessage: Optional[str] = None


class DeploymentStatus(BaseModel):
    instances: dict[str, Instance] = {}
    modules: dict[str, Module] = {}
    deploymentId: Optional[str] = None
    reconcileStatus: Optional[ReconcileStatus] = None


class SystemInfoV2(BaseModel, MessageBuilder):
    systemInfo: SystemInfo = SystemInfo()
    state_agent_report_status_interval_min: int = 3
    state_agent_report_status_interval_max: int = 180
    deploymentStatus: DeploymentStatus = DeploymentStatus()
    state_agent_registry_auth: dict = {}
    state_agent_configuration_id: str = ""

    def build(self) -> MqttMessage:
        payload = {
            "systemInfo": self.systemInfo.model_dump(),
            "state/$agent/report-status-interval-min": self.state_agent_report_status_interval_min,
            "state/$agent/report-status-interval-max": self.state_agent_report_status_interval_max,
            "deploymentStatus": self.deploymentStatus.model_dump(exclude_none=True),
        }
        if self.deploymentStatus.deploymentId:
            payload.update(
                {
                    "state/$agent/registry-auth": self.state_agent_registry_auth,
                    "state/$agent/configuration-id": self.state_agent_configuration_id,
                }
            )

        return MqttMessage(
            topic=MqttTopics.ATTRIBUTES.value,
            payload=json_bytes(payload),
        )


class ResInfoNoID(BaseModel):
    code: int
    detail_msg: str


class DirectGetImageResponse(BaseModel):
    res_info: ResInfoNoID
    image: str


class DirectGetImageRequest(BaseModel):
    sensor_name: str = "sensor_chip"
    flip_horizontal: int | None = None
    flip_vertical: int | None = None
    crop_h_offset: int | None = None
    crop_v_offset: int | None = None
    crop_h_size: int | None = None
    crop_v_size: int | None = None
    network_id: str | None = None


class DirectCommandResponseBody(BaseModel):
    status: str = "ok"
    reqid: str
    response: str
    errorMessage: str | None = None


class DirectCommandResponse(BaseModel):
    direct_command_response: DirectCommandResponseBody = Field(
        alias="direct-command-response",
    )

    model_config = ConfigDict(populate_by_name=True)
