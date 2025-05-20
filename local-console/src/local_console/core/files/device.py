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
from abc import ABC
from abc import abstractmethod
from datetime import datetime
from pathlib import Path

from local_console.core.camera.machine import Camera
from local_console.core.camera.streaming import image_dir_for
from local_console.core.camera.streaming import inference_dir_for
from local_console.core.device_services import DeviceServices
from local_console.core.files.exceptions import FileNotFound
from local_console.core.schemas.schemas import DeviceID

logger = logging.getLogger(__name__)


class BaseFileManager(ABC):
    def __init__(self, device_services: DeviceServices) -> None:
        self.device_services = device_services

    def _find_device(self, device_id: DeviceID) -> Camera:
        cam = self.device_services.get_camera(device_id)
        if not cam:
            logger.debug(f"Could not find device {device_id}")
            raise FileNotFound(
                filename=f"device {device_id}",
                message=f"Device for port {device_id} not found",
            )
        return cam

    @abstractmethod
    def _path_from(self, camera_state: Camera) -> Path: ...

    def _base_folder(self, device_id: DeviceID) -> Path:
        camera_state = self._find_device(device_id)
        return self._path_from(camera_state)

    def list_for(self, device_id: DeviceID) -> list[Path]:
        base_dir: Path = self._base_folder(device_id)
        logger.debug(f"Listing the contents of the folder: {base_dir}")
        return sorted(
            (file for file in base_dir.iterdir() if file.is_file()), reverse=True
        )[0:999]

    def get_file(self, device_id: DeviceID, file_name: str) -> Path:
        file = self._base_folder(device_id) / file_name
        if not file.is_file():
            raise FileNotFound(
                filename=file_name, message=f"File '{file_name}' does not exist"
            )
        return file


class ImageFileManager(BaseFileManager):
    def __init__(self, device_services: DeviceServices) -> None:
        super().__init__(device_services)

    def _path_from(self, camera: Camera) -> Path:
        target_dir = image_dir_for(camera.id)
        assert target_dir, f"Image folder not set for device {camera.id}"
        return Path(target_dir)

    def with_preview(self, device_id: DeviceID) -> bool:
        camera = self._find_device(device_id)
        return camera.preview_mode.active

    def get_preview(self, device_id: DeviceID) -> bytes:
        camera = self._find_device(device_id)
        return camera.preview_mode.get()

    def ts_preview(self, device_id: DeviceID) -> datetime | None:
        camera = self._find_device(device_id)
        return camera.preview_mode.last_updated


class InferenceFileManager(BaseFileManager):
    def __init__(self, device_services: DeviceServices) -> None:
        super().__init__(device_services)

    def _path_from(self, camera: Camera) -> Path:
        target_dir = inference_dir_for(camera.id)
        assert target_dir, f"Inference folder not set for device {camera.id}"
        return Path(target_dir)
