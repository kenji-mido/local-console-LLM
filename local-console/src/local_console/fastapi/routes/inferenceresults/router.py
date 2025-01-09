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

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Path
from fastapi import Query
from fastapi import status
from fastapi.responses import JSONResponse
from local_console.core.camera.flatbuffers import flatbuffer_binary_to_json
from local_console.core.files.inference import Inference
from local_console.fastapi.routes.devices.configuration.dependencies import (
    InjectCameraConfigurationController,
)
from local_console.fastapi.routes.inferenceresults.dependencies import (
    InjectInferencesController,
)
from local_console.fastapi.routes.inferenceresults.dto import InferenceListDTO


router = APIRouter(prefix="/inferenceresults", tags=["Inferences"])


@router.get("/devices/{device_id}")
async def list(
    controller: InjectInferencesController,
    device_id: int = Path(description="Device ID. Device mqtt port"),
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
) -> InferenceListDTO:
    return controller.list(device_id, limit, starting_after)


@router.get("/devices/{device_id}/json")
async def flatbuffers_to_json(
    controller: InjectCameraConfigurationController,
    flatbuffer_payload: str,
    device_id: int = Path(description="Device ID. Device mqtt port"),
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


@router.get("/devices/{device_id}/{inference_id}")
async def get_by_id(
    controller: InjectInferencesController,
    device_id: int = Path(description="Device ID. Device mqtt port"),
    inference_id: str = Path(description="Inference ID."),
) -> Inference:
    return controller.get(device_id, inference_id)
