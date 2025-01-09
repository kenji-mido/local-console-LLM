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
from typing import Any

from local_console.core.camera.schemas import DeviceStateInformation
from pydantic import BaseModel
from pydantic import RootModel


class DevicePostDTO(BaseModel):
    device_name: str
    mqtt_port: int


class DeviceListDTO(BaseModel):
    continuation_token: str = ""
    devices: list[DeviceStateInformation]


class RPCRequestDTO(BaseModel):
    command_name: str
    parameters: dict[str, Any]


class RPCResponseDTO(BaseModel):
    result: str = "SUCCESS"
    command_response: Any


class Configuration(RootModel):
    root: dict[str, str | int | float | dict]

    def __getitem__(self, item: str) -> str | int | float | dict:
        return self.root[item]

    def to_dict(self) -> dict[str, str | int | float | dict]:
        return self.root


class PropertyInfo(BaseModel):
    configuration: dict[str, Configuration]

    def get_property_name_and_values(self) -> tuple[str, dict]:
        name = ""
        config_dict = {}
        for name, value in self.configuration.items():
            config_dict = value.to_dict()
            break
        return name, config_dict


class ConfigurationUpdateInDTO(BaseModel):
    property: PropertyInfo


class ConfigurationUpdateOutDTO(ConfigurationUpdateInDTO):
    result: str = "SUCCESS"
