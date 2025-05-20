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
from base64 import b64decode
from pathlib import Path as PathLib
from typing import Annotated

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Path
from fastapi import Query
from fastapi import status
from fastapi.responses import JSONResponse
from local_console.core.camera.flatbuffers import flatbuffer_binary_to_json
from local_console.core.files.inference import InferenceOut
from local_console.core.schemas.schemas import DeviceID
from local_console.fastapi.routes.devices.configuration.dependencies import (
    InjectCameraConfigurationController,
)
from local_console.fastapi.routes.images.dependencies import InjectImagesController
from local_console.fastapi.routes.inferenceresults.dependencies import (
    InjectInferencesController,
)
from local_console.fastapi.routes.inferenceresults.dto import InferenceListDTO
from local_console.fastapi.routes.inferenceresults.dto import InferenceWithImageListDTO


router = APIRouter(prefix="/inferenceresults", tags=["Inferences"])


@router.get(
    "/devices/{device_id}",
    description="Returns the model information and inference data from a specific device.",
)
async def list(
    controller: InjectInferencesController,
    device_id: DeviceID,
    limit: Annotated[
        int,
        Query(
            ge=0,
            le=256,
            description="Specify the maximum number of objects to return in a single call. This parameter is required. Default: 20",
        ),
    ] = 20,
    starting_after: Annotated[
        str | None,
        Query(
            description="Return objects strictly after the one identified by this value. Use it together with 'continuation_token' from previous calls in order to perform pagination."
        ),
    ] = None,
) -> InferenceListDTO:
    return controller.list(device_id, limit, starting_after)


@router.get(
    "/devices/{device_id}/withimage",
    description="Returns complete entries of (inference, image) data from a specific device.",
)
async def list_with_images(
    controller: InjectInferencesController,
    img_controller: InjectImagesController,
    device_id: DeviceID,
    limit: Annotated[
        int,
        Query(
            ge=0,
            le=256,
            description="Specify the maximum number of objects to return in a single call. This parameter is required. Default: 20",
        ),
    ] = 20,
    starting_after: Annotated[
        str | None,
        Query(
            description="Return objects strictly after the one identified by this value. Use it together with 'continuation_token' from previous calls in order to perform pagination."
        ),
    ] = None,
) -> InferenceWithImageListDTO:
    return controller.list_with_images(device_id, img_controller, limit, starting_after)


@router.get(
    "/devices/{device_id}/json",
    description="Decodes a flatbuffer containing the result of an inference, and returns it as a stringified JSON.",
)
async def flatbuffers_to_json(
    controller: InjectCameraConfigurationController,
    flatbuffer_payload: Annotated[
        str,
        Query(
            description="Payload encoded in base 64 that's been previously serialized in any of the supported inference flatbuffer schemas. Currently supporting classification or detection"
        ),
    ],
    device_id: DeviceID,
) -> JSONResponse:
    schema_file = controller.get_schema_by_id(device_id)
    if not schema_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device schema not configured",
        )

    if not PathLib(schema_file).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device schema does not exists",
        )

    try:
        decoded_payload = b64decode(flatbuffer_payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Base64-encoded payload: {e}",
        )

    try:
        json_content = flatbuffer_binary_to_json(PathLib(schema_file), decoded_payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to convert FlatBuffer to JSON: {e}",
        )

    return JSONResponse(content=json_content, status_code=status.HTTP_200_OK)


@router.get(
    "/devices/{device_id}/{id}",
    description="Returns a specific inference result from a specific device.",
)
async def get_by_id(
    controller: InjectInferencesController,
    device_id: DeviceID,
    id: Annotated[
        str,
        Path(
            description="Unique ID identifying a single inference result from a device"
        ),
    ],
) -> InferenceOut:
    return controller.get(device_id, id)
