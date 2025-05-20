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
from typing import Any

from local_console.core.camera.v2.components.device_capabilities import (
    DeviceCapabilities,
)
from local_console.core.camera.v2.components.device_info import DeviceInfo
from local_console.core.camera.v2.components.device_states import DeviceStates
from local_console.core.camera.v2.components.network_settings import NetworkSettings
from local_console.core.camera.v2.components.private_deploy_ai_model import (
    PrivateDeployAIModel,
)
from local_console.core.camera.v2.components.private_deploy_firmware import (
    PrivateDeployFirmware,
)
from local_console.core.camera.v2.components.private_endpoint_settings import (
    PrivateEndpointSettings,
)
from local_console.core.camera.v2.components.private_reserved import PrivateReserved
from local_console.core.camera.v2.components.system_info import SystemInfo
from local_console.core.camera.v2.components.system_settings import SystemSettings
from local_console.core.camera.v2.components.wireless_settings import WirelessSetting
from local_console.core.config import Config
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator


class EdgeSystemCommon(BaseModel):
    # Reported by EVP Agent
    system_info: SystemInfo | None = Field(default=None, alias="systemInfo")
    report_status_interval_min: int | None = Field(
        default=None,
        validation_alias="state/$agent/report-status-interval-min",
        serialization_alias="configuration/$agent/report-status-interval-min",
    )
    report_status_interval_max: int | None = Field(
        default=None,
        validation_alias="state/$agent/report-status-interval-max",
        serialization_alias="configuration/$agent/report-status-interval-max",
    )
    deployment_status: dict | None = Field(default=None, alias="deploymentStatus")

    # Reported by System App
    device_info: DeviceInfo | None = Field(
        default=None,
        validation_alias="state/$system/device_info",
        serialization_alias="configuration/$system/device_info",
    )
    device_capabilities: DeviceCapabilities | None = Field(
        default=None,
        validation_alias="state/$system/device_capabilities",
        serialization_alias="configuration/$system/device_capabilities",
    )
    device_states: DeviceStates | None = Field(
        default=None,
        validation_alias="state/$system/device_states",
        serialization_alias="configuration/$system/device_states",
    )
    system_settings: SystemSettings | None = Field(
        default=None,
        validation_alias="state/$system/system_settings",
        serialization_alias="configuration/$system/system_settings",
    )
    network_settings: NetworkSettings | None = Field(
        default=None,
        validation_alias="state/$system/network_settings",
        serialization_alias="configuration/$system/network_settings",
    )
    wireless_setting: WirelessSetting | None = Field(
        default=None,
        validation_alias="state/$system/wireless_setting",
        serialization_alias="configuration/$system/wireless_setting",
    )
    private_endpoint_setting: PrivateEndpointSettings | None = Field(
        default=None,
        validation_alias="state/$system/PRIVATE_endpoint_settings",
        serialization_alias="configuration/$system/PRIVATE_endpoint_settings",
    )
    private_reserved: PrivateReserved | None = Field(
        default=None,
        validation_alias="state/$system/PRIVATE_reserved",
        serialization_alias="configuration/$system/PRIVATE_reserved",
    )
    private_deploy_ai_model: PrivateDeployAIModel | None = Field(
        default=None,
        validation_alias="state/$system/PRIVATE_deploy_ai_model",
        serialization_alias="configuration/$system/PRIVATE_deploy_ai_model",
    )
    private_deploy_firmware: PrivateDeployFirmware | None = Field(
        default=None,
        validation_alias="state/$system/PRIVATE_deploy_firmware",
        serialization_alias="configuration/$system/PRIVATE_deploy_firmware",
    )

    # Missing properties:
    # - periodic_setting for T3W
    # and the commands:
    # - reboot
    # - factory_reset
    # - read_sensor_register
    # - write_sensor_register
    # - event_log
    # - auto_enrollment

    # Reported by Edge App

    # {"state/A/edge_app": B, "state/X/edge_app": Y} -> {"A": B, "X": Y}
    edge_app: dict[str, dict] = {}

    model_config = ConfigDict(validate_assignment=True, populate_by_name=True)

    @field_validator(
        "system_info",
        "deployment_status",
        "device_info",
        "device_capabilities",
        "device_states",
        "system_settings",
        "network_settings",
        "wireless_setting",
        "private_endpoint_setting",
        "private_reserved",
        "private_deploy_ai_model",
        "private_deploy_firmware",
        mode="before",
    )
    @classmethod
    def to_dict(cls, data: Any) -> Any:
        # Device reports attributes as strings. This methods converts the string into a JSON.
        if isinstance(data, str):
            return json.loads(data)
        return data

    @model_validator(mode="before")
    @classmethod
    def collect_edge_apps(cls, values: dict[str, Any]) -> dict[str, Any]:
        edge_app: dict[str, dict] = {}
        for key in list(values.keys()):
            if key.startswith("state/") and key.endswith("/edge_app"):
                parts = key.split("/")
                if len(parts) == 3:
                    group = parts[1]  # Get Edge App name. I.e., "node"
                    edge_app[group] = cls.to_dict(values.pop(key))
        values["edge_app"] = edge_app
        return values


def update_not_none_fields(
    source: EdgeSystemCommon, target: EdgeSystemCommon
) -> EdgeSystemCommon:
    target_dict = target.model_dump(exclude_none=True)
    for key, value in target_dict.items():
        setattr(source, key, value)
    return source


def update_mqtt_endpoint(edge_sys_common: EdgeSystemCommon) -> None:
    if edge_sys_common.private_endpoint_setting:
        for device in Config().data.devices:
            if (
                device.mqtt.port
                == edge_sys_common.private_endpoint_setting.endpoint_port
            ):
                device.mqtt.host = edge_sys_common.private_endpoint_setting.endpoint_url
                Config().save_config()
                break
