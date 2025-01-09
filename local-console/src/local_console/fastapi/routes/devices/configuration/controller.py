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
from typing import Any
from venv import logger

from fastapi import HTTPException
from fastapi import status
from local_console.core.camera.enums import ApplicationType
from local_console.core.camera.state import CameraState
from local_console.core.device_services import DeviceServices
from local_console.core.enums import ApplicationSchemaFilePath
from local_console.fastapi.routes.commons import EmptySuccess
from local_console.fastapi.routes.devices.configuration.dto import (
    CameraConfigurationDTO,
)

logger = logging.getLogger(__name__)


class CameraConfigurationController:

    def __init__(self, device_service: DeviceServices) -> None:
        self.device_service = device_service

    def _preamble(self, device_id: int) -> CameraState:
        if device_id not in self.device_service.states:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find device {device_id}",
            )
        return self.device_service.states[device_id]

    def get_by_id(self, device_id: int) -> CameraConfigurationDTO:
        cam_state = self._preamble(device_id)

        def as_str_or_none(e: Any) -> str | None:
            return str(e) if e else None

        return CameraConfigurationDTO(
            image_dir_path=as_str_or_none(cam_state.image_dir_path.value),
            inference_dir_path=as_str_or_none(cam_state.inference_dir_path.value),
            size=cam_state.size.value,
            unit=cam_state.unit.value,
            vapp_type=cam_state.vapp_type.value,
            vapp_config_file=as_str_or_none(cam_state.vapp_config_file.value),
            vapp_labels_file=as_str_or_none(cam_state.vapp_labels_file.value),
        )

    def get_schema_by_id(self, device_id: int) -> Path | None:
        schema_file = self._preamble(device_id).vapp_schema_file.value
        return Path(schema_file) if schema_file else None

    async def update(
        self, device_id: int, settings: CameraConfigurationDTO
    ) -> EmptySuccess:
        cam_state = self._preamble(device_id)

        for field in CameraConfigurationDTO.model_fields.keys():
            var = getattr(cam_state, field)
            new_val = getattr(settings, field)
            # Since endpoint is patch, None refers to not used attribute.
            # E.g., to remove `vapp_config_file` the value has to be an empty string.
            if new_val and var.value != new_val:
                logger.debug(f"Updating {field} to {new_val}")
                await var.aset(new_val)

        if settings.vapp_type:
            await cam_state.vapp_schema_file.aset(
                {
                    ApplicationType.CLASSIFICATION: ApplicationSchemaFilePath.CLASSIFICATION,
                    ApplicationType.DETECTION: ApplicationSchemaFilePath.DETECTION,
                }[settings.vapp_type]
            )

        return EmptySuccess()
