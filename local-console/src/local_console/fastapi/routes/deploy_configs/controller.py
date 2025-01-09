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
from local_console.core.deploy.config_deployer import ConfigDeployer
from local_console.core.deploy.deployment_manager import DeploymentManager
from local_console.core.deploy_config import DeployConfigIn
from local_console.core.deploy_config import DeployConfigManager
from local_console.core.deploy_config import EdgeAppIn
from local_console.fastapi.routes.commons import EmptySuccess
from local_console.fastapi.routes.deploy_configs.dto import ConfigFileRequestDTO
from local_console.fastapi.routes.deploy_configs.dto import DeployByConfigurationDTO
from local_console.fastapi.routes.deploy_configs.dto import EdgeSystemSwPackage


class DeployConfigController:
    def __init__(
        self,
        deploy_config_manager: DeployConfigManager,
        deployer: ConfigDeployer,
        deployment_manager: DeploymentManager,
    ):
        self.deploy_config_manager = deploy_config_manager
        self.deployer = deployer
        self.deployment_manager = deployment_manager

    def _to_deploy_config(self, request: ConfigFileRequestDTO) -> DeployConfigIn:
        firmware_ids = []
        if isinstance(request.edge_system_sw_package, EdgeSystemSwPackage):
            firmware_ids.append(request.edge_system_sw_package.firmware_id)
        if isinstance(request.edge_system_sw_package, list):
            ids = [fw.firmware_id for fw in request.edge_system_sw_package]
            firmware_ids.extend(ids)

        model_ids = [model.model_id for model in request.models]
        edge_apps = [
            EdgeAppIn(
                edge_app_id=edge_app.edge_app_package_id,
                version=edge_app.app_version,
            )
            for edge_app in request.edge_apps
        ]

        return DeployConfigIn(
            config_id=request.config_id,
            fw_ids=firmware_ids,
            model_ids=model_ids,
            edge_apps=edge_apps,
        )

    def register(self, request: ConfigFileRequestDTO) -> EmptySuccess:
        self.deploy_config_manager.register(self._to_deploy_config(request))
        return EmptySuccess()

    async def deploy(
        self, devices: DeployByConfigurationDTO, config_id: str
    ) -> EmptySuccess:
        for device_id in devices.device_ids:
            task_entity = await self.deployer.deploy(device_id, config_id)
            self.deployment_manager.add_device_to_deployment(task_entity.id, device_id)
        return EmptySuccess()
