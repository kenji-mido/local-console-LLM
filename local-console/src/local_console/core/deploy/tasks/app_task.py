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

from local_console.core.camera.enums import DeployStage
from local_console.core.camera.state import CameraState
from local_console.core.deploy.tasks.base_task import DeployHistoryInfo
from local_console.core.deploy.tasks.base_task import Status
from local_console.core.deploy.tasks.base_task import Task
from local_console.core.deploy.tasks.base_task import TaskState
from local_console.core.edge_apps import EdgeApp
from local_console.utils.trio import DEFAULT_TASK_TIMEOUT
from local_console.utils.trio import EVENT_WAITING
from local_console.utils.trio import TimeoutConfig

logger = logging.getLogger(__name__)


class AppDeployHistoryInfo(DeployHistoryInfo):
    app_name: str
    app_version: str | None
    description: str | None
    status: Status | None = None


class AppTask(Task):
    def __init__(
        self,
        camera_state: CameraState,
        app: EdgeApp,
        task_state: TaskState | None = None,
        timeout: TimeoutConfig = TimeoutConfig(
            timeout_in_seconds=DEFAULT_TASK_TIMEOUT.timeout_in_seconds,
            pollin_interval_in_seconds=EVENT_WAITING.pollin_interval_in_seconds,
        ),
    ):
        self._camera_state = camera_state
        self._app = app
        self._task_state = task_state or TaskState()
        self._timeout = timeout

    def _has_finished(self) -> bool:
        return (
            not self._camera_state._deploy_fsm
            or self._camera_state._deploy_fsm.stage == DeployStage.Done
        )

    async def _change_state(
        self, new: DeployStage | None, prev: DeployStage | None
    ) -> None:
        logger.debug(
            f"AppTask has received a new state {new} the previous one was {prev}"
        )
        if new == DeployStage.Done:
            self._task_state.set(Status.SUCCESS)
        if new == DeployStage.Error:
            self._task_state.set(Status.ERROR)

    async def run(self) -> None:
        try:
            self._task_state.set(Status.RUNNING)
            self._camera_state.deploy_stage.subscribe_async(self._change_state)
            self._camera_state.module_file.value = self._app.file.path
            await self._camera_state.do_app_deployment()
            await self.timeout().wait_for(
                lambda: self._task_state.get() in [Status.ERROR, Status.SUCCESS]
            )
            if self._task_state.get() not in [Status.ERROR, Status.SUCCESS]:
                self._task_state.error_notification(
                    f"Could not deploy app {self._app.info.edge_app_package_id} in {self.timeout().timeout_in_seconds} seconds."
                )
        finally:
            self._camera_state.deploy_stage.unsubscribe_async(self._change_state)

    def get_state(self) -> TaskState:
        return self._task_state

    def errored(self, error: BaseException) -> None:
        self._task_state.handle_exception(error)

    async def stop(self) -> None:
        await EVENT_WAITING.wait_for(lambda: self._camera_state._deploy_fsm is not None)
        if self._camera_state._deploy_fsm:
            self._task_state.error_notification("Task has been externally stopped")
            self._camera_state._deploy_fsm.stop()
            await self._camera_state._deploy_fsm._set_new_stage(DeployStage.Error)

    def id(self) -> str:
        assert self._camera_state.mqtt_port.value, "Id of the camera is needed"
        return f"app_task_for_device_{self._camera_state.mqtt_port.value}"

    def timeout(self) -> TimeoutConfig:
        return self._timeout

    def get_deploy_history_info(self) -> AppDeployHistoryInfo:
        return AppDeployHistoryInfo(
            app_name=self._app.info.app_name,
            app_version=self._app.info.app_version,
            description=self._app.info.description,
            status=self._task_state.get(),
        )
