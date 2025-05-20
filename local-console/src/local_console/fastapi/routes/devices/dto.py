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
from local_console.core.schemas.schemas import DeviceID
from local_console.utils.enums import StrEnum
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class DevicePostDTO(BaseModel):
    device_name: str
    id: DeviceID


class DeviceListDTO(BaseModel):
    continuation_token: str = ""
    devices: list[DeviceStateInformation]


class RPCRequestDTO(BaseModel):
    command_name: str = Field(
        description="Specify the command to execute on the server. Valid values are <code>StartUploadInferenceData</code> and <code>StopUploadInferenceData</code>."
    )
    parameters: dict[str, Any] = Field(
        description="Provide a dictionary of arguments to pass to the specified command. The required arguments depend on the command:"
        "<br>- For <code>StartUploadInferenceData</code>:"
        "<pre>{"
        '<br>    "CropHOffset": int,'
        '<br>    "CropVOffset": int,'
        '<br>    "CropHSize": int,'
        '<br>    "CropVSize": int,'
        '<br>    "Mode": [0, 1, 2]  // 0 for gathering images only, 1 for performing inference as well, 2 for sending only the inference'
        "<br>}</pre>"
        "<br>- For <code>StopUploadInferenceData</code>:"
        "<pre>{}</pre>"
    )
    extra: dict[str, Any] | None = Field(
        default=None,
        description="Optional data not included in the RPC's payload, for the API to implement custom logic.",
    )


class RPCDeviceResponse(BaseModel):
    result: str = "Accepted"

    model_config = ConfigDict(extra="allow")


class RPCResponseResult(StrEnum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


class RPCResponseDTO(BaseModel):
    result: RPCResponseResult = RPCResponseResult.SUCCESS
    command_response: dict | None


class PropertyInfo(BaseModel):
    configuration: dict[str, dict]

    def get_property_name_and_values(self) -> tuple[str, dict]:
        name = ""
        config_dict = {}
        for name, value in self.configuration.items():
            config_dict = value
            break
        return name, config_dict


class ConfigurationUpdateInDTO(BaseModel):
    property: PropertyInfo


class ConfigurationUpdateOutDTO(PropertyInfo):
    result: str = "SUCCESS"


class StateOutDTO(BaseModel):
    state: dict
