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
from datetime import datetime
from unittest.mock import MagicMock

from local_console.core.deploy.tasks.app_task import AppDeployHistoryInfo
from local_console.core.deploy.tasks.base_task import Task
from local_console.core.deploy.tasks.firmware_task import FirmwareDeployHistoryInfo
from local_console.core.deploy.tasks.firmware_task import FirmwareTask
from local_console.core.deploy.tasks.model_task import ModelDeployHistoryInfo
from local_console.core.deploy.tasks.task_executors import TaskEntity
from local_console.core.deploy_config import DeployConfig
from local_console.core.schemas.schemas import Deployment
from local_console.core.schemas.schemas import InstanceSpec
from local_console.core.schemas.schemas import Module
from local_console.fastapi.routes.deploy_history.dto import DeployHistory
from local_console.utils.timing import now

from tests.strategies.samplers.files import FirmwareSampler


class DeployHistorySampler:
    def __init__(
        self,
        deploy_id: str = "deploy_id",
        from_datetime: datetime = now(),
        deploy_type: str = "ConfigTask",
        deploying_cnt: int = 0,
        success_cnt: int = 1,
        fail_cnt: int = 0,
        deploy_config: DeployConfig | None = None,
    ) -> None:
        self.deploy_id = deploy_id
        self.from_datetime = from_datetime
        self.deploy_type = deploy_type
        self.deploying_cnt = deploying_cnt
        self.success_cnt = success_cnt
        self.fail_cnt = fail_cnt
        self.deploy_config = deploy_config

    def sample(self) -> DeployHistory:
        history = DeployHistory(
            deploy_id=self.deploy_id,
            from_datetime=self.from_datetime,
            deploy_type=self.deploy_type,
            deploying_cnt=self.deploying_cnt,
            success_cnt=self.success_cnt,
            fail_cnt=self.fail_cnt,
        )
        if self.deploy_config:
            history.config_id = self.deploy_config.config_id
            history.edge_apps = [
                AppDeployHistoryInfo(
                    app_name=app.info.app_name,
                    app_version=app.info.app_version,
                    description=app.info.description,
                )
                for app in self.deploy_config.edge_apps
            ]
            history.edge_system_sw_package = [
                FirmwareDeployHistoryInfo(
                    firmware_id=firmware.firmware_id,
                    firmware_version=firmware.info.version,
                )
                for firmware in self.deploy_config.firmwares
            ]
            history.models = [
                ModelDeployHistoryInfo(model_id=model.info.model_id)
                for model in self.deploy_config.models
            ]
        return history


class TaskEntitySampler:
    def __init__(
        self,
        id: str = "id",
        task: Task = FirmwareTask(MagicMock(), FirmwareSampler().sample()),
    ) -> None:
        self.id = id
        self.task = task

    def sample(self) -> TaskEntity:
        return TaskEntity(id=self.id, task=self.task)


class DeploymentSampler:
    def __init__(
        self,
        id: str = "id",
    ) -> None:
        self.id = id

    def sample(self, num_modules: int = 0) -> Deployment:

        modules = {
            f"mod_{i}": Module(
                entryPoint="main",
                moduleImpl="wasm",
                downloadUrl="",
                hash="",
            )
            for i in range(num_modules)
        }
        instances = {
            f"inst_{name}": InstanceSpec(
                moduleId=name,
                subscribe={},
                publish={},
            )
            for name in modules.keys()
        }

        return Deployment(
            deploymentId=self.id,
            instanceSpecs=instances,
            modules=modules,
            publishTopics={},
            subscribeTopics={},
        )
