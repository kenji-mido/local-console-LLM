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
from local_console.core.camera.enums import ConnectionState
from pydantic import BaseModel
from pydantic import field_validator


class MSInfo(BaseModel):
    name: str | None = None
    firmware_version: str
    loader_version: str | None = None


class MSAIModel(BaseModel):
    name: str | None = None
    version: str | None = None
    converter_version: str | None = None


class MSDeviceInfo(BaseModel):
    processors: list[MSInfo] | None = None
    sensors: list[MSInfo] | None = None
    ai_models: list[MSAIModel] | None = None


class MSDeviceState(BaseModel):
    process_state: str | None = None

    @field_validator("process_state")
    @classmethod
    def validate_process_state_value(cls, v: str) -> str:
        valid_states = {
            None,
            "Idle",
            "Aborted",
            "InstallationMode",
            "PowerSaving",
            "FactoryReset",
            "FactoryResetDone",
        }
        if v not in valid_states:
            raise ValueError(
                f"Given state {v} is not a valid one. Please choose one from: {valid_states}"
            )
        return v


class MSPeriodicSetting(BaseModel):
    ip_addr_setting: str | None = None

    @field_validator("ip_addr_setting")
    @classmethod
    def validate_ip_addr_setting(cls, v: str) -> str:
        valid_ip_addr_setting = {
            None,
            "save",
            "dhcp",
        }
        if v not in valid_ip_addr_setting:
            raise ValueError(
                f"Given ip_addr_setting {v} is not a valid one. Please choose one from: {valid_ip_addr_setting}"
            )
        return v


class MSNetworkSettings(BaseModel):
    ntp_url: str | None = None
    gateway_address: str | None = None
    subnet_mask: str | None = None
    ip_address: str | None = None
    dns_address: str | None = None
    proxy_url: str | None = None
    proxy_port: int | None = None
    proxy_user_name: str | None = None


class MSSSIDSetting(BaseModel):
    ssid: str | None = None
    password: str | None = None


class MSWirelessSetting(BaseModel):
    sta_mode_setting: MSSSIDSetting = MSSSIDSetting()
    ap_mode_setting: MSSSIDSetting = MSSSIDSetting()


class MSPrivateEndpointSettings(BaseModel):
    endpoint_url: str | None = None
    endpoint_port: int | None = None


class MState(BaseModel):
    device_info: MSDeviceInfo = MSDeviceInfo()
    device_state: MSDeviceState = MSDeviceState()
    periodic_setting: MSPeriodicSetting = MSPeriodicSetting()
    network_settings: MSNetworkSettings = MSNetworkSettings()
    wireless_setting: MSWirelessSetting = MSWirelessSetting()
    PRIVATE_endpoint_settings: MSPrivateEndpointSettings = MSPrivateEndpointSettings()


class MProperty(BaseModel):
    state: MState = MState()


class ModuleInfo(BaseModel):
    module_id: str = "$system"
    property: MProperty = MProperty()


class DeviceStateInformation(BaseModel):
    device_name: str
    device_id: str
    description: str
    internal_device_id: str
    port: int
    connection_state: ConnectionState
    inactivity_timeout: int = 0
    device_groups: list = []
    modules: list[ModuleInfo] | None = None
