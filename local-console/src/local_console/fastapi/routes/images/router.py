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
from fastapi import APIRouter
from fastapi import Path
from fastapi import Query
from fastapi.responses import FileResponse
from local_console.fastapi.routes.images.dependencies import InjectImagesController
from local_console.fastapi.routes.images.dto import FileListDTO


router = APIRouter(prefix="/images", tags=["Images"])


@router.get("/devices/{device_id}/directories/{sub_directory_name}")
@router.get("/devices/{device_id}/directories")
async def list(
    controller: InjectImagesController,
    device_id: int = Path(description="Device ID. Device mqtt port"),
    sub_directory_name: str = Path(
        default_factory=lambda: "",
        description="This parameter is primarily included for compatibility with SCS and does not affect the response",
    ),
    limit: int = Query(
        50,
        ge=0,
        le=256,
        description="Number of the items to fetch information",
    ),
    starting_after: str | None = Query(
        None,
        description="Retrieves additional data beyond the number of targets specified by the query parameter (limit). Specify the value obtained from the response (continuation_token) to fetch the next data.",
    ),
) -> FileListDTO:
    return controller.list(device_id, limit, starting_after)


@router.get("/devices/{device_id}/image/{image_name}")
async def download(
    controller: InjectImagesController,
    device_id: int = Path(description="Device ID. Device mqtt port"),
    image_name: str = Path(description="Name of image to download"),
) -> FileResponse:
    return controller.download(device_id, image_name)
