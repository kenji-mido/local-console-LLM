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
from datetime import datetime
from pathlib import Path

from local_console.core.config import Config
from local_console.core.schemas.schemas import DeviceID
from local_console.utils.timing import now


# Webserver constants
PREVIEW_TARGET = "pre"


class PreviewBuffer:
    """
    Encapsulates the operation of preview mode that holds
    the most recent image from the camera in-memory, hence
    avoiding the file system.
    """

    def __init__(self) -> None:
        self._in_preview = False
        self._data = b""
        self._timestamp: datetime | None = None

    @property
    def active(self) -> bool:
        return self._in_preview

    @property
    def last_updated(self) -> datetime | None:
        return self._timestamp

    def enable(self) -> None:
        self._in_preview = True

    def disable(self) -> None:
        self._in_preview = False

    def get(self) -> bytes:
        return self._data

    def update(self, data: bytes) -> None:
        self._data = data
        self._timestamp = now()


def base_dir_for(device_id: DeviceID, base: Path | None = None) -> Path | None:
    base = base or Config().get_persistent_attr(device_id, "device_dir_path")
    return base / str(device_id) if base else None


def dir_for(
    device_id: DeviceID, subfolder: str, base: Path | None = None
) -> Path | None:
    base_dir = base_dir_for(device_id, base)
    return base_dir / subfolder if base_dir else None


def image_dir_for(device_id: DeviceID, base: Path | None = None) -> Path | None:
    return dir_for(device_id, "Images", base)


def inference_dir_for(device_id: DeviceID, base: Path | None = None) -> Path | None:
    return dir_for(device_id, "Metadata", base)
