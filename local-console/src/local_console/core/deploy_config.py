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
from local_console.core.edge_apps import EdgeApp
from local_console.core.edge_apps import EdgeAppsManager
from local_console.core.files.exceptions import FileNotFound
from local_console.core.firmwares import Firmware
from local_console.core.firmwares import FirmwareManager
from local_console.core.models import Model
from local_console.core.models import ModelManager
from pydantic import BaseModel
from pydantic import ConfigDict


class EdgeAppIn(BaseModel):
    edge_app_id: str
    version: str


class DeployConfigIn(BaseModel):
    config_id: str
    fw_ids: list[str]
    edge_apps: list[EdgeAppIn]
    model_ids: list[str]

    model_config = ConfigDict(protected_namespaces=())


class DeployConfig(BaseModel):
    config_id: str
    firmwares: list[Firmware]
    edge_apps: list[EdgeApp]
    models: list[Model]


class DeployConfigManager:
    def __init__(
        self,
        model_manager: ModelManager,
        edge_app_manager: EdgeAppsManager,
        fw_manager: FirmwareManager,
    ) -> None:
        self._deploy_configs: dict[str, DeployConfigIn] = {}
        self._fw_manager = fw_manager
        self._edge_app_manager = edge_app_manager
        self._model_manager = model_manager

    def register(self, config: DeployConfigIn) -> None:
        # POST /deploy_config contain the version of the app
        # add version in edge_app object
        for edge_app_in in config.edge_apps:
            edge_app = self._edge_app_manager.get_by_id(edge_app_in.edge_app_id)
            if not edge_app:
                raise FileNotFound(
                    f"Edge app id {edge_app_in.edge_app_id} not registered"
                )
            edge_app.info.app_version = edge_app_in.version

        self._to_detail_or_fail(config)
        self._deploy_configs[config.config_id] = config

    def get_by_id(self, config_id: str) -> DeployConfig | None:
        if config_id not in self._deploy_configs:
            return None
        return self._to_detail_or_fail(self._deploy_configs[config_id])

    def _to_detail_or_fail(self, config: DeployConfigIn) -> DeployConfig:
        firmwares = self._get_fws_or_fail(config.fw_ids)
        apps = self._get_apps_or_fail(config.edge_apps)
        models = self._get_models_or_fail(config.model_ids)
        return DeployConfig(
            config_id=config.config_id,
            firmwares=firmwares,
            edge_apps=apps,
            models=models,
        )

    def _get_models_or_fail(self, model_ids: list[str]) -> list[Model]:
        models: list[Model] = []
        for model_id in model_ids:
            model_info = self._model_manager.get_by_id(model_id)
            if not model_info:
                raise FileNotFound(f"Model id {model_id} not registered")
            models.append(model_info)
        return models

    def _get_apps_or_fail(self, edge_apps: list[EdgeAppIn]) -> list[EdgeApp]:
        apps: list[EdgeApp] = []
        for edge_app in edge_apps:
            edge_apps_info = self._edge_app_manager.get_by_id(edge_app.edge_app_id)
            if not edge_apps_info:
                raise FileNotFound(f"Edge app id {edge_app.edge_app_id} not registered")
            apps.append(edge_apps_info)
        return apps

    def _get_fws_or_fail(self, firmware_ids: list[str]) -> list[Firmware]:
        fws: list[Firmware] = []
        for firmware_id in firmware_ids:
            fw_info = self._fw_manager.get_by_id(firmware_id)
            if not fw_info:
                raise FileNotFound(f"Firmware id {firmware_id} not registered")
            fws.append(fw_info)
        return fws
