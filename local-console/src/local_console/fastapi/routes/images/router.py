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
from typing import Annotated

from fastapi import APIRouter
from fastapi import Path
from fastapi import Query
from fastapi.responses import FileResponse
from fastapi.responses import Response
from local_console.core.schemas.schemas import DeviceID
from local_console.fastapi.routes.images.dependencies import InjectImagesController
from local_console.fastapi.routes.images.dto import FileListDTO


router = APIRouter(prefix="/images", tags=["Images"])


@router.get(
    "/devices/{device_id}/directories",
    description="Returns the filenames and paths of the images obtained from the specified device.",
)
async def list(
    controller: InjectImagesController,
    device_id: DeviceID,
    limit: Annotated[
        int,
        Query(
            ge=0,
            le=256,
            description="Specify the maximum number of objects to return in a single call. This parameter is required. Default: 50",
        ),
    ] = 50,
    starting_after: Annotated[
        str | None,
        Query(
            description="Return objects strictly after the one identified by this value. Use it together with 'continuation_token' from previous calls in order to perform pagination."
        ),
    ] = None,
) -> FileListDTO:
    return controller.list(device_id, limit, starting_after)


@router.get(
    "/devices/{device_id}/image/{image_name}",
    description="Returns a specific image from the specified device.",
)
async def download(
    controller: InjectImagesController,
    device_id: DeviceID,
    image_name: Annotated[
        str,
        Path(description="Filename of the specific image to be retrieved"),
    ],
) -> FileResponse:
    return controller.download(device_id, image_name)


@router.get(
    "/devices/{device_id}/preview",
    description="Returns the preview image from the specified device.",
)
async def preview(
    controller: InjectImagesController,
    device_id: DeviceID,
) -> Response:
    return controller.get_preview(device_id)
