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

import trio
from local_console.core.camera.enums import ApplicationConfiguration
from local_console.core.camera.machine import Camera
from local_console.core.commands.deploy import single_module_manifest_setup
from local_console.core.deploy.tasks.base_task import DeployHistoryInfo
from local_console.core.deploy.tasks.base_task import Status
from local_console.core.deploy.tasks.base_task import Task
from local_console.core.deploy.tasks.base_task import TaskState
from local_console.core.edge_apps import EdgeApp

logger = logging.getLogger(__name__)


class AppDeployHistoryInfo(DeployHistoryInfo):
    app_name: str
    app_version: str | None
    description: str | None
    status: Status | None = None


class AppTask(Task):
    def __init__(
        self,
        camera: Camera,
        app: EdgeApp,
        task_state: TaskState | None = None,
    ):
        self._camera = camera
        self._app = app
        self._task_state = task_state or TaskState()
        self._task_state.set(Status.INITIALIZING)

    def _error(self, message: str) -> None:
        self._task_state.error_notification(message)

    async def run(self) -> None:
        task_flag = trio.Event()
        self._task_state.set(Status.RUNNING)

        spec = single_module_manifest_setup(
            ApplicationConfiguration.NAME,  # May be better to use self._app.info.app_name
            self._app.file.path,
        )
        await self._camera.start_app_deployment(spec, task_flag, self._error)
        await task_flag.wait()
        self._task_state.set(Status.SUCCESS)

    def get_state(self) -> TaskState:
        return self._task_state

    def errored(self, error: BaseException) -> None:
        self._task_state.handle_exception(error)

    async def stop(self) -> None:
        if self._task_state.get() == Status.INITIALIZING:
            return

        self._task_state.error_notification("Task has been externally stopped")
        await self._camera.stop_app_deployment()

    def id(self) -> str:
        assert self._camera.id, "Id of the camera is needed"
        return f"app_task_for_device_{self._camera.id}"

    def get_deploy_history_info(self) -> AppDeployHistoryInfo:
        return AppDeployHistoryInfo(
            app_name=self._app.info.app_name,
            app_version=self._app.info.app_version,
            description=self._app.info.description,
            status=self._task_state.get(),
        )
