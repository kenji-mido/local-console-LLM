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
from fastapi import APIRouter
from local_console.fastapi.routes.commons import EmptySuccess
from local_console.fastapi.routes.deploy_configs.dependencies import (
    InjectDeployConfigController,
)
from local_console.fastapi.routes.deploy_configs.dto import ConfigFileRequestDTO
from local_console.fastapi.routes.deploy_configs.dto import DeployByConfigurationDTO


router = APIRouter(prefix="/deploy_configs", tags=["Config"])


@router.post("")
async def post_deployment(
    request: ConfigFileRequestDTO,
    controller: InjectDeployConfigController,
) -> EmptySuccess:
    return controller.register(request)


@router.post("/{config_id}/apply")
async def apply_deployment(
    config_id: str,
    devices: DeployByConfigurationDTO,
    controller: InjectDeployConfigController,
) -> EmptySuccess:
    return await controller.deploy(devices=devices, config_id=config_id)
