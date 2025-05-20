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
from local_console.core.schemas.schemas import DeviceID
from pydantic import BaseModel
from pydantic import ConfigDict


class Model(BaseModel):
    model_id: str
    model_version_number: str

    model_config = ConfigDict(protected_namespaces=())


class EdgeSystemSwPackage(BaseModel):
    firmware_id: str


class EdgeApp(BaseModel):
    edge_app_package_id: str
    app_name: str
    app_version: str


class ConfigFileRequestDTO(BaseModel):
    config_id: str = ""
    description: str = ""
    models: list[Model] = []
    edge_system_sw_package: None | EdgeSystemSwPackage | list[EdgeSystemSwPackage] = (
        None
    )
    edge_apps: list[EdgeApp] = []


class DeployByConfigurationDTO(BaseModel):
    device_ids: list[DeviceID]
    description: str
