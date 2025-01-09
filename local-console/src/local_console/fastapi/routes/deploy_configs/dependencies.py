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
from local_console.core.deploy.config_deployer import ConfigDeployer
from local_console.fastapi.dependencies.commons import InjectDeployBackgroundTask
from local_console.fastapi.dependencies.commons import InjectGlobalConfig
from local_console.fastapi.dependencies.deploy import InjectDeployConfigManager
from local_console.fastapi.dependencies.deploy import InjectDeploymentManager
from local_console.fastapi.dependencies.devices import InjectDeviceServices
from local_console.fastapi.routes.deploy_configs.controller import (
    DeployConfigController,
)


def deploy_config_controller(
    config_manager: InjectDeployConfigManager,
    devices: InjectDeviceServices,
    tasks: InjectDeployBackgroundTask,
    deployment_manager: InjectDeploymentManager,
    config: InjectGlobalConfig,
) -> DeployConfigController:
    deployer = ConfigDeployer(
        devices=devices,
        configs=config_manager,
        tasks=tasks,
        params=config.config.config.deployment,
    )
    return DeployConfigController(
        deployer=deployer,
        deploy_config_manager=config_manager,
        deployment_manager=deployment_manager,
    )


InjectDeployConfigController = Annotated[
    DeployConfigController, Depends(deploy_config_controller)
]
