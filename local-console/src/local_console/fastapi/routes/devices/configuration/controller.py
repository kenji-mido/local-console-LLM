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
from pathlib import Path

from fastapi import HTTPException
from fastapi import status
from local_console.core.camera.enums import ApplicationType
from local_console.core.camera.machine import Camera
from local_console.core.config import Config
from local_console.core.device_services import DeviceServices
from local_console.core.enums import ApplicationSchemaFilePath
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes
from local_console.core.schemas.schemas import DeviceID
from local_console.core.schemas.schemas import Persist
from local_console.fastapi.routes.devices.configuration.dto import (
    CameraConfigurationDTO,
)
from local_console.fastapi.routes.devices.configuration.dto import Status
from local_console.fastapi.routes.devices.configuration.dto import StatusType
from local_console.utils.fstools import StorageSizeWatcher

logger = logging.getLogger(__name__)
config_obj = Config()


class CameraConfigurationController:

    def __init__(self, device_service: DeviceServices) -> None:
        self.device_service = device_service

    def _create_updated_config(
        self, device_id: DeviceID, requested: CameraConfigurationDTO
    ) -> Persist:
        current = config_obj.get_device_config(device_id).persist.model_copy(deep=True)
        current.device_dir_path = requested.device_dir_path or current.device_dir_path
        current.size = requested.size or current.size
        current.unit = requested.unit or current.unit
        current.ai_model_file = requested.ai_model_file or current.ai_model_file
        current.module_file = requested.module_file or current.module_file
        current.auto_deletion = (
            current.auto_deletion
            if requested.auto_deletion is None
            else requested.auto_deletion
        )
        current.vapp_config_file = (
            requested.vapp_config_file or current.vapp_config_file
        )
        current.vapp_labels_file = (
            requested.vapp_labels_file or current.vapp_labels_file
        )
        current.vapp_type = requested.vapp_type or current.vapp_type
        if current.vapp_type:
            current.vapp_schema_file = {
                ApplicationType.CLASSIFICATION: str(
                    ApplicationSchemaFilePath.CLASSIFICATION
                ),
                ApplicationType.DETECTION: str(ApplicationSchemaFilePath.DETECTION),
            }.get(current.vapp_type, "")

        return current

    def _preamble(self, device_id: DeviceID) -> Camera:
        cam = self.device_service.get_camera(device_id)
        if not cam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find device {device_id}",
            )
        return cam

    def get_by_id(self, device_id: DeviceID) -> CameraConfigurationDTO:
        cam = self._preamble(device_id)
        persist = config_obj.get_device_config(device_id).persist

        return CameraConfigurationDTO(
            device_dir_path=persist.device_dir_path,
            size=persist.size,
            unit=persist.unit,
            vapp_type=persist.vapp_type,
            vapp_config_file=persist.vapp_config_file,
            vapp_labels_file=persist.vapp_labels_file,
            ai_model_file=persist.ai_model_file,
            module_file=persist.module_file,
            auto_deletion=persist.auto_deletion,
            status={
                StatusType.STORAGE_USAGE: Status(
                    value=cam.current_storage_usage(),
                )
            },
        )

    def get_schema_by_id(self, device_id: DeviceID) -> Path | None:
        schema_file = config_obj.get_device_config(device_id).persist.vapp_schema_file
        return Path(schema_file) if schema_file else None

    async def update(
        self, device_id: DeviceID, settings: CameraConfigurationDTO
    ) -> None:
        camera = self._preamble(device_id)
        updated_config = self._create_updated_config(device_id, settings)
        camera.update_storage_config(updated_config)
        config_obj.get_device_config(device_id).persist = updated_config
        config_obj.save_config()

    def validate(
        self, device_id: DeviceID, settings: CameraConfigurationDTO
    ) -> dict[StatusType, Status]:
        updated_config = self._create_updated_config(device_id, settings)
        storage_size_watcher = StorageSizeWatcher(updated_config)

        status = {}
        try:
            storage_size_watcher.apply(updated_config, device_id)
        except UserException as e:
            if e.code == ErrorCodes.EXTERNAL_CANNOT_USE_DIRECTORY:
                status[StatusType.FOLDER_ERROR] = Status()
        status[StatusType.STORAGE_USAGE] = Status(value=storage_size_watcher.size())
        return status
