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
from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.camera.schemas import PropertiesReport
from local_console.core.deploy.tasks.config_task import ConfigTask
from local_console.core.deploy.tasks.task_executors import TaskEntity
from local_console.core.deploy.tasks.task_executors import TaskExecutor
from local_console.core.deploy_config import DeployConfigManager
from local_console.core.device_services import DeviceServices
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes
from local_console.core.firmwares import Firmware
from local_console.core.schemas.schemas import DeploymentConfig
from local_console.core.schemas.schemas import DeviceID


class ConfigDeployer:
    def __init__(
        self,
        devices: DeviceServices,
        configs: DeployConfigManager,
        tasks: TaskExecutor,
        params: DeploymentConfig,
    ) -> None:
        self.devices = devices
        self.configs = configs
        self.tasks = tasks
        self.params = params

    def _validate_firmware(self, current: PropertiesReport, firmware: Firmware) -> None:
        if firmware.info.firmware_type == OTAUpdateModule.SENSORFW:
            if firmware.info.version == current.sensor_fw_version:
                raise UserException(
                    ErrorCodes.EXTERNAL_FIRMWARE_SAME_VERSION,
                    "Already same Firmware version is available",
                )

        if firmware.info.firmware_type == OTAUpdateModule.APFW:
            if firmware.info.version == current.cam_fw_version:
                raise UserException(
                    ErrorCodes.EXTERNAL_FIRMWARE_SAME_VERSION,
                    "Already same Firmware version is available",
                )

    def _validate(self, task: ConfigTask) -> None:
        for firmware in task._config.firmwares:
            self._validate_firmware(task._camera._common_properties.reported, firmware)

    async def deploy(self, device_id: DeviceID, config_id: str) -> TaskEntity:
        camera = self.devices.get_camera(device_id)
        if not camera:
            raise FileNotFoundError(f"Device with id {device_id} not found.")
        config = self.configs.get_by_id(config_id)
        if not config:
            raise FileNotFoundError(f"Config with id {config_id} not found.")
        task = ConfigTask(camera, config, self.params)
        self._validate(task)
        return await self.tasks.add_task(task)
