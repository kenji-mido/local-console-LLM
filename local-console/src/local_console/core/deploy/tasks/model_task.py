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
from local_console.core.camera.ai_model import deployment_task
from local_console.core.camera.state import CameraState
from local_console.core.deploy.tasks.base_task import DeployHistoryInfo
from local_console.core.deploy.tasks.base_task import Status
from local_console.core.deploy.tasks.base_task import Task
from local_console.core.deploy.tasks.base_task import TaskState
from local_console.core.models import Model
from local_console.core.schemas.schemas import ModelDeploymentConfig
from local_console.utils.trio import TimeoutConfig


class ModelDeployHistoryInfo(DeployHistoryInfo):
    model_id: str
    status: Status | None = None


class ModelTask(Task):
    def __init__(
        self,
        state: CameraState,
        model: Model,
        task_state: TaskState | None = None,
        params: ModelDeploymentConfig = ModelDeploymentConfig(),
    ) -> None:
        self.camera_state = state
        self.model = model
        self._task_state = task_state or TaskState()
        self._task_state.set(Status.INITIALIZING)
        self.timeout_undeploy = TimeoutConfig(
            timeout_in_seconds=params.undeploy_timeout
        )
        self.timeout_deploy = TimeoutConfig(timeout_in_seconds=params.deploy_timeout)

    def _error(self, message: str) -> None:
        self._task_state.error_notification(message)

    async def run(self) -> None:
        self._task_state.set(Status.RUNNING)
        await deployment_task(
            self.camera_state,
            self.model.file.path,
            self._error,
            self.timeout_undeploy,
            self.timeout_deploy,
        )
        self._task_state.set(Status.SUCCESS)

    def get_state(self) -> TaskState:
        return self._task_state

    def errored(self, error: BaseException) -> None:
        self._task_state.handle_exception(error)

    async def stop(self) -> None:
        self._task_state.error_notification("Task has been externally stopped")
        # There is no nice way to close the firmware task internals

    def id(self) -> str:
        assert self.camera_state.mqtt_port.value, "Id of the camera is needed"
        return f"model_task_for_device_{self.camera_state.mqtt_port.value}"

    def get_deploy_history_info(self) -> ModelDeployHistoryInfo:
        return ModelDeployHistoryInfo(
            model_id=self.model.info.model_id, status=self._task_state.get()
        )
