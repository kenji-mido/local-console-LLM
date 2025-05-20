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

from fastapi import HTTPException
from fastapi import status
from fastapi.responses import FileResponse
from fastapi.responses import Response
from local_console.core.error.base import UserException
from local_console.core.files.device import ImageFileManager
from local_console.core.schemas.schemas import DeviceID
from local_console.fastapi.pagination import Paginator
from local_console.fastapi.routes.images.dto import FileDTO
from local_console.fastapi.routes.images.dto import FileListDTO
from local_console.utils.timing import as_timestamp


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

    def _to_file_dto(self, img: Path, device_id: DeviceID) -> FileDTO:
        return FileDTO(
            name=img.name, sas_url=f"/images/devices/{device_id}/image/{img.name}"
        )

    def list(
        self, device_id: DeviceID, limit: int, starting_after: str | None
    ) -> FileListDTO:
        paths = self.image_manager.list_for(device_id)
        trimmed, continuation = self.paginator.paginate(paths, limit, starting_after)
        listing = FileListDTO(
            data=[self._to_file_dto(image, device_id) for image in trimmed],
            continuation_token=continuation,
        )
        try:
            in_preview = self.image_manager.with_preview(device_id)
        except UserException:
            in_preview = False

        if starting_after is None and in_preview:
            ts = self.image_manager.ts_preview(device_id)
            if ts:
                preview_dto = FileDTO(
                    name=as_timestamp(ts) + ".jpg",
                    sas_url=f"/images/devices/{device_id}/preview",
                )
                listing.data.insert(0, preview_dto)

        return listing

    def download(self, device_id: DeviceID, image_name: str) -> FileResponse:
        image = self.image_manager.get_file(device_id, image_name)
        return FileResponse(path=image, filename=image.name)

    def get_preview(self, device_id: DeviceID) -> Response:
        ts = self.image_manager.ts_preview(device_id)
        if ts:
            filename = as_timestamp(ts) + ".jpg"
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No preview image has been received yet from the device.",
            )

        image = self.image_manager.get_preview(device_id)
        return Response(
            content=image,
            media_type="image/jpg",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
