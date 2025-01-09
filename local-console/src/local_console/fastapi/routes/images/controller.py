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
from pathlib import Path

from fastapi.responses import FileResponse
from local_console.core.files.device import ImageFileManager
from local_console.fastapi.pagination import Paginator
from local_console.fastapi.routes.images.dto import FileDTO
from local_console.fastapi.routes.images.dto import FileListDTO


class ImagePaginator(Paginator):
    @classmethod
    def _get_element_key(cls, element: Path) -> str:
        return element.name


class ImagesController:
    def __init__(
        self, image_manager: ImageFileManager, paginator: ImagePaginator | None = None
    ) -> None:
        self.image_manager = image_manager
        self.paginator = paginator or ImagePaginator()

    def _to_file_dto(self, img: Path, device_id: int) -> FileDTO:
        return FileDTO(
            name=img.name, sas_url=f"/images/devices/{device_id}/image/{img.name}"
        )

    def list(
        self, device_id: int, limit: int, starting_after: str | None
    ) -> FileListDTO:
        paths = self.image_manager.list_for(device_id)
        trimmed, continuation = self.paginator.paginate(paths, limit, starting_after)
        return FileListDTO(
            data=[self._to_file_dto(image, device_id) for image in trimmed],
            continuation_token=continuation,
        )

    def download(self, device_id: int, image_name: str) -> FileResponse:
        image = self.image_manager.get_file(device_id, image_name)
        return FileResponse(path=image, filename=image.name)
