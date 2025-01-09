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
from typing import Annotated

from fastapi import Depends
from fastapi import Request
from local_console.core.deploy.deployment_manager import DeploymentManager
from local_console.core.deploy_config import DeployConfigManager
from local_console.core.edge_apps import EdgeAppsManager
from local_console.core.firmwares import FirmwareManager
from local_console.core.models import ModelManager
from local_console.fastapi.dependencies.commons import file_manager
from local_console.fastapi.dependencies.devices import InjectDeviceServices


def model_manager(request: Request) -> ModelManager:
    app = request.app
    if not hasattr(app.state, "model_manager"):
        model_manager = ModelManager(file_manager(request))
        app.state.model_manager = model_manager
    assert isinstance(app.state.model_manager, ModelManager)
    return app.state.model_manager


def edge_apps_manager(request: Request) -> EdgeAppsManager:
    app = request.app
    if not hasattr(app.state, "edge_apps_manager"):
        edge_apps_manager = EdgeAppsManager(file_manager(request))
        app.state.edge_apps_manager = edge_apps_manager
    assert isinstance(app.state.edge_apps_manager, EdgeAppsManager)
    return app.state.edge_apps_manager


def firmware_manager(request: Request) -> FirmwareManager:
    app = request.app
    if not hasattr(app.state, "firmware_manager"):
        firmware_manager = FirmwareManager(file_manager(request))
        app.state.firmware_manager = firmware_manager
    assert isinstance(app.state.firmware_manager, FirmwareManager)
    return app.state.firmware_manager


def deploy_config_manager(request: Request) -> DeployConfigManager:
    app = request.app
    if not hasattr(app.state, "deploy_config_manager"):
        app.state.deploy_config_manager = DeployConfigManager(
            model_manager=model_manager(request),
            fw_manager=firmware_manager(request),
            edge_app_manager=edge_apps_manager(request),
        )
    assert isinstance(app.state.deploy_config_manager, DeployConfigManager)
    return app.state.deploy_config_manager


def deployment_manager(
    request: Request,
    device_service: InjectDeviceServices,
) -> DeploymentManager:
    app = request.app
    if not hasattr(app.state, "deployment_manager"):
        app.state.deployment_manager = DeploymentManager(device_service=device_service)
    assert isinstance(app.state.deployment_manager, DeploymentManager)
    return app.state.deployment_manager


InjectModelManager = Annotated[ModelManager, Depends(model_manager)]

InjectFirmwareManager = Annotated[FirmwareManager, Depends(firmware_manager)]

InjectEdgeAppsManager = Annotated[EdgeAppsManager, Depends(edge_apps_manager)]

InjectDeployConfigManager = Annotated[
    DeployConfigManager, Depends(deploy_config_manager)
]

InjectDeploymentManager = Annotated[DeploymentManager, Depends(deployment_manager)]
