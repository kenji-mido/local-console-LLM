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
from local_console.core.camera.enums import FirmwareExtension
from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.camera.firmware import FirmwareInfo
from local_console.core.camera.machine import Camera
from local_console.core.commands.ota_deploy import get_package_hash
from local_console.core.deploy.tasks.base_task import DeployHistoryInfo
from local_console.core.deploy.tasks.base_task import Status
from local_console.core.deploy.tasks.base_task import Task
from local_console.core.deploy.tasks.base_task import TaskState
from local_console.core.firmwares import Firmware

logger = logging.getLogger(__name__)


class FirmwareDeployHistoryInfo(DeployHistoryInfo):
    firmware_id: str
    firmware_version: str
    status: Status | None = None


class FirmwareTask(Task):
    def __init__(
        self,
        camera: Camera,
        firmware: Firmware,
        task_state: TaskState | None = None,
    ):
        self.camera = camera
        self.firmware = firmware
        self._task_state = task_state or TaskState()

    def get_state(self) -> TaskState:
        return self._task_state

    @staticmethod
    def _prepare_firmware_info(firmware: Firmware) -> FirmwareInfo:
        fw_path = firmware.file.path
        fw_type = firmware.info.firmware_type

        is_valid = (
            fw_type == OTAUpdateModule.APFW
            and fw_path.suffix == FirmwareExtension.APPLICATION_FW
        ) or (
            fw_type == OTAUpdateModule.SENSORFW
            and fw_path.suffix == FirmwareExtension.SENSOR_FW
        )

        return FirmwareInfo(
            path=fw_path,
            hash=get_package_hash(firmware.file.path),
            type=fw_type,
            version=firmware.info.version,
            is_valid=is_valid,
        )

    async def run(self) -> None:
        task_flag = trio.Event()
        self._task_state.set(Status.RUNNING)
        await self.camera.perform_firmware_update(
            self._prepare_firmware_info(self.firmware),
            task_flag,
            self._task_state.error_notification,
        )
        await task_flag.wait()
        self._task_state.set(Status.SUCCESS)

    def errored(self, error: BaseException) -> None:
        self._task_state.handle_exception(error)

    async def stop(self) -> None:
        self._task_state.error_notification("Task has been externally stopped")
        # There is no nice way to close the firmware task internals

    def id(self) -> str:
        return f"firmware_task_for_device_{self.camera.id}"

    def get_deploy_history_info(self) -> FirmwareDeployHistoryInfo:
        return FirmwareDeployHistoryInfo(
            firmware_id=self.firmware.firmware_id,
            firmware_version=self.firmware.info.version,
            status=self._task_state.get(),
        )
