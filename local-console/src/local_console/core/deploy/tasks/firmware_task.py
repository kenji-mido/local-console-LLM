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

from local_console.core.camera.firmware import TransientStatus
from local_console.core.camera.firmware import update_firmware_task
from local_console.core.camera.state import CameraState
from local_console.core.deploy.tasks.base_task import DeployHistoryInfo
from local_console.core.deploy.tasks.base_task import Status
from local_console.core.deploy.tasks.base_task import Task
from local_console.core.deploy.tasks.base_task import TaskState
from local_console.core.firmwares import Firmware

logger = logging.getLogger(__name__)


class FirmwareTransientStatus(TransientStatus):
    update_status: str
    progress_download: int
    progress_update: int


class FirmwareDeployHistoryInfo(DeployHistoryInfo):
    firmware_id: str
    firmware_version: str
    status: Status | None = None


class FirmwareTask(Task):
    def __init__(
        self,
        state: CameraState,
        firmware: Firmware,
        task_state: TaskState | None = None,
    ):
        self.camera_state = state
        self.firmware = firmware
        self._task_state = task_state or TaskState()

    def get_state(self) -> TaskState:
        return self._task_state

    async def run(self) -> None:
        self._task_state.set(Status.RUNNING)
        self.camera_state.firmware_file.value = self.firmware.file.path
        self.camera_state.firmware_file_type.value = self.firmware.info.firmware_type
        self.camera_state.firmware_file_version.value = self.firmware.info.version
        await update_firmware_task(
            self.camera_state,
            self._task_state.error_notification,
        )
        self.camera_state.firmware_file.value = None
        self.camera_state.firmware_file_type.value = None
        self.camera_state.firmware_file_version.value = None
        self._task_state.set(Status.SUCCESS)

    def errored(self, error: BaseException) -> None:
        self._task_state.handle_exception(error)

    async def stop(self) -> None:
        self._task_state.error_notification("Task has been externally stopped")
        # There is no nice way to close the firmware task internals

    def id(self) -> str:
        assert self.camera_state.mqtt_port.value, "Id of the camera is needed"
        return f"firmware_task_for_device_{self.camera_state.mqtt_port.value}"

    def get_deploy_history_info(self) -> FirmwareDeployHistoryInfo:
        return FirmwareDeployHistoryInfo(
            firmware_id=self.firmware.firmware_id,
            firmware_version=self.firmware.info.version,
            status=self._task_state.get(),
        )
