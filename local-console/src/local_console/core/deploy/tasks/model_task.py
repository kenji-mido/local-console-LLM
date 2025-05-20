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
import trio
from local_console.core.camera.machine import Camera
from local_console.core.deploy.tasks.base_task import DeployHistoryInfo
from local_console.core.deploy.tasks.base_task import Status
from local_console.core.deploy.tasks.base_task import Task
from local_console.core.deploy.tasks.base_task import TaskState
from local_console.core.models import Model
from local_console.core.schemas.schemas import ModelDeploymentConfig
from pydantic import ConfigDict


class ModelDeployHistoryInfo(DeployHistoryInfo):
    model_id: str
    status: Status | None = None

    model_config = ConfigDict(protected_namespaces=())


class ModelTask(Task):
    def __init__(
        self,
        camera: Camera,
        model: Model,
        task_state: TaskState | None = None,
        params: ModelDeploymentConfig = ModelDeploymentConfig(),
    ) -> None:
        self.camera = camera
        self.model = model
        self._task_state = task_state or TaskState()
        self._task_state.set(Status.INITIALIZING)
        self.timeout_undeploy = params.undeploy_timeout
        self.timeout_deploy = params.deploy_timeout

    def _error(self, message: str) -> None:
        self._task_state.error_notification(message)

    async def run(self) -> None:
        task_flag = trio.Event()
        self._task_state.set(Status.RUNNING)
        await self.camera.deploy_sensor_model(
            self.model.file.path,
            task_flag,
            self._error,
            self.timeout_undeploy,
            self.timeout_deploy,
        )
        await task_flag.wait()
        self._task_state.set(Status.SUCCESS)

    def get_state(self) -> TaskState:
        return self._task_state

    def errored(self, error: BaseException) -> None:
        self._task_state.handle_exception(error)

    async def stop(self) -> None:
        self._task_state.error_notification("Task has been externally stopped")
        # There is no nice way to close the firmware task internals

    def id(self) -> str:
        assert self.camera.id, "Id of the camera is needed"
        return f"model_task_for_device_{self.camera.id}"

    def get_deploy_history_info(self) -> ModelDeployHistoryInfo:
        return ModelDeployHistoryInfo(
            model_id=self.model.info.model_id, status=self._task_state.get()
        )
