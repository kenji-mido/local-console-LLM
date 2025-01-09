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
from pathlib import Path

from local_console.core.camera.state import CameraState
from local_console.core.device_services import DeviceServices
from local_console.core.files.exceptions import FileNotFound

logger = logging.getLogger(__name__)


class BaseFileManager(ABC):
    def __init__(self, device_services: DeviceServices) -> None:
        self.device_services = device_services

    def _find_device(self, device_id: int) -> CameraState:
        try:
            state = self.device_services.states[device_id]
            return state
        except KeyError as e:
            logger.debug(f"Could not find device {device_id}", exc_info=e)
            raise FileNotFound(
                filename=f"device {device_id}",
                message=f"Device for port {device_id} not found",
            )

    @abstractmethod
    def _path_from(self, camera_state: CameraState) -> Path: ...

    def _base_folder(self, device_id: int) -> Path:
        camera_state = self._find_device(device_id)
        return self._path_from(camera_state)

    def list_for(self, device_id: int) -> list[Path]:
        image_dir: Path = self._base_folder(device_id)
        logger.debug(f"Listing the contents of the folder: {image_dir}")
        return sorted(
            (file for file in image_dir.iterdir() if file.is_file()), reverse=True
        )[0:999]

    def get_file(self, device_id: int, file_name: str) -> Path:
        file = self._base_folder(device_id) / file_name
        if not file.is_file():
            raise FileNotFound(
                filename=file_name, message=f"File '{file_name}' does not exist"
            )
        return file


class ImageFileManager(BaseFileManager):
    def __init__(self, device_services: DeviceServices) -> None:
        super().__init__(device_services)

    def _path_from(self, camera_state: CameraState) -> Path:
        assert (
            camera_state.image_dir_path.value
        ), f"There is not image folder for device {camera_state.mqtt_port.value}"
        return Path(camera_state.image_dir_path.value)


class InferenceFileManager(BaseFileManager):
    def __init__(self, device_services: DeviceServices) -> None:
        super().__init__(device_services)

    def _path_from(self, camera_state: CameraState) -> Path:
        assert (
            camera_state.inference_dir_path.value
        ), f"There is not inference folder for device {camera_state.mqtt_port.value}"
        return Path(camera_state.inference_dir_path.value)
