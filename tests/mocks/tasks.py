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
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import trio
from local_console.core.deploy.tasks.app_task import AppTask
from local_console.core.deploy.tasks.base_task import Status
from local_console.core.deploy.tasks.base_task import Task
from local_console.core.deploy.tasks.base_task import TaskState
from local_console.core.deploy.tasks.config_task import ConfigTask
from local_console.core.deploy.tasks.firmware_task import FirmwareTask
from local_console.core.deploy.tasks.model_task import ModelTask
from local_console.core.schemas.schemas import DeploymentConfig
from local_console.utils.random import random_id
from local_console.utils.trio import TaskStatus
from local_console.utils.trio import TimeoutConfig

from tests.strategies.samplers.files import DeployConfigSampler
from tests.strategies.samplers.files import EdgeAppSampler
from tests.strategies.samplers.files import FirmwareSampler
from tests.strategies.samplers.files import ModelSampler

SHORT_TIMEOUT = TimeoutConfig(
    timeout_in_seconds=0.005, pollin_interval_in_seconds=0.005
)


class WaitingTasks(Task):
    def __init__(
        self,
        timeout: TimeoutConfig = SHORT_TIMEOUT,
        status_manager: TaskState | None = None,
    ):
        self._timeout = timeout
        self.task_state = status_manager or TaskState()
        self.stopped: bool = False

    def get_state(self) -> TaskStatus:
        return self.task_state

    async def run(self) -> None:
        self.task_state.set(Status.RUNNING)
        for i in range(self._timeout.num_of_iterations()):
            if self.stopped:
                break
            await trio.sleep(
                self._timeout.pollin_interval_in_seconds
            )  # simulate long running task
        self.task_state.set(Status.SUCCESS)

    async def stop(self) -> None:
        self.stopped = True

    def errored(self, error: BaseException) -> None:
        self.task_state.error_notification(str(error))
        self.stopped = True

    def id(self) -> str:
        id = random_id()
        return f"waiting_tasks_{id}"


def mocked_task(timeout: TimeoutConfig = SHORT_TIMEOUT) -> WaitingTasks:
    task = WaitingTasks(timeout=timeout)
    task.run = AsyncMock(side_effect=task.run)
    task.stop = AsyncMock(side_effect=task.stop)
    task.get_state = MagicMock(side_effect=task.get_state)
    task.errored = MagicMock(side_effect=task.errored)
    task.timeout = MagicMock(side_effect=task.timeout)
    task.id = MagicMock(side_effect=task.id)
    return task


def mocked_firmware_tasks(firmware=FirmwareSampler().sample()) -> FirmwareTask:
    task = FirmwareTask(AsyncMock(), firmware)
    task.run = AsyncMock(side_effect=task.run)
    task.stop = AsyncMock(side_effect=task.stop)
    return task


def mocked_app_tasks(app=EdgeAppSampler().sample()) -> AppTask:
    state = AsyncMock()
    state._deploy_fsm.stop = MagicMock()
    task = AppTask(state, app)
    task.run = AsyncMock(side_effect=task.run)
    task.stop = AsyncMock(side_effect=task.stop)
    return task


def mocked_model_tasks(app=ModelSampler().sample()) -> ModelTask:
    task = ModelTask(AsyncMock(), app)
    task.run = AsyncMock(side_effect=task.run)
    task.stop = AsyncMock(side_effect=task.stop)
    return task


def mocked_config_tasks(config=DeployConfigSampler().sample()) -> ConfigTask:
    task = ConfigTask(AsyncMock(), config, DeploymentConfig())
    task.run = AsyncMock(side_effect=task.run)
    return task
