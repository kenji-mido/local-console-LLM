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
import logging

from local_console.core.camera.state import CameraState
from local_console.core.deploy.tasks.app_task import AppDeployHistoryInfo
from local_console.core.deploy.tasks.app_task import AppTask
from local_console.core.deploy.tasks.base_task import DeployHistoryInfo
from local_console.core.deploy.tasks.base_task import Status
from local_console.core.deploy.tasks.base_task import Task
from local_console.core.deploy.tasks.base_task import TaskState
from local_console.core.deploy.tasks.firmware_task import FirmwareDeployHistoryInfo
from local_console.core.deploy.tasks.firmware_task import FirmwareTask
from local_console.core.deploy.tasks.model_task import ModelDeployHistoryInfo
from local_console.core.deploy.tasks.model_task import ModelTask
from local_console.core.deploy_config import DeployConfig
from local_console.core.schemas.schemas import DeploymentConfig
from local_console.utils.trio import TimeoutConfig

logger = logging.getLogger(__name__)


class ConfigDeployHistoryInfo(DeployHistoryInfo):
    config_id: str
    edge_system_sw_package: list[FirmwareDeployHistoryInfo]
    models: list[ModelDeployHistoryInfo]
    edge_apps: list[AppDeployHistoryInfo]


class ConfigTask(Task):
    def __init__(
        self, state: CameraState, config: DeployConfig, params: DeploymentConfig
    ) -> None:
        self._camera_state = state
        self._config = config
        self._tasks = self._calc_all_tasks(state, config, params)

    def get_state(self) -> TaskState:
        if not self._tasks:
            return TaskState(status=Status.SUCCESS)
        early_start = (
            min(self._tasks, key=lambda task: task.get_state().started_at)
            .get_state()
            .started_at
        )
        for task in self._tasks:
            task_state = task.get_state()
            if task_state.status == Status.ERROR:
                return task_state.that_started_at(early_start)

        if all(t.get_state() == Status.SUCCESS for t in self._tasks):
            return TaskState(status=Status.SUCCESS, started_at=early_start)

        if all(t.get_state() == Status.INITIALIZING for t in self._tasks):
            return TaskState(status=Status.INITIALIZING, started_at=early_start)

        return TaskState(status=Status.RUNNING, started_at=early_start)

    def _calc_all_tasks(
        self, state: CameraState, config: DeployConfig, params: DeploymentConfig
    ) -> list[Task]:
        tasks: list[Task] = []
        for firmware in config.firmwares:
            tasks.append(FirmwareTask(state, firmware))
        for app in config.edge_apps:
            tasks.append(AppTask(state, app))
        for model in config.models:
            tasks.append(ModelTask(state, model, params=params.model))
        return tasks

    async def run(self) -> None:
        for task in self._tasks:
            await task.run()

    def errored(self, error: BaseException) -> None:
        for task in self._tasks:
            task.errored(error)

    def timeout(self) -> TimeoutConfig:
        timeout = 0.0
        for task in self._tasks:
            timeout = timeout + task.timeout().timeout_in_seconds
        return TimeoutConfig(
            pollin_interval_in_seconds=timeout, timeout_in_seconds=timeout
        )

    async def stop(self) -> None:
        for task in self._tasks:
            if task.get_state().status == Status.RUNNING:
                await task.stop()

    def id(self) -> str:
        assert self._camera_state.mqtt_port.value, "Id of the camera is needed"
        return f"config_task_for_device_{self._camera_state.mqtt_port.value}"

    def _get_info(self, task_type: type[Task]) -> list[DeployHistoryInfo]:
        return [
            task.get_deploy_history_info()
            for task in self._tasks
            if isinstance(task, task_type)
        ]

    def get_deploy_history_info(self) -> ConfigDeployHistoryInfo:
        edge_apps = self._get_info(AppTask)
        return ConfigDeployHistoryInfo(
            edge_system_sw_package=self._get_info(FirmwareTask),  # type: ignore
            models=self._get_info(ModelTask),  # type: ignore
            edge_apps=edge_apps,  # type: ignore
            config_id=self._config.config_id,
        )
