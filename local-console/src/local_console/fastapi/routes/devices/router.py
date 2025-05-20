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
from fastapi import HTTPException
from fastapi import Query
from fastapi import status
from local_console.core.camera.enums import ConnectionState
from local_console.core.camera.schemas import DeviceStateInformation
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes
from local_console.core.schemas.schemas import DeviceID
from local_console.fastapi.exception_documentation import (
    ExternalDeviceNotFoundDocumentationMessage,
)
from local_console.fastapi.routes.commons import EmptySuccess
from local_console.fastapi.routes.devices.configuration.dependencies import (
    InjectCameraConfigurationController,
)
from local_console.fastapi.routes.devices.configuration.dto import (
    CameraConfigurationDTO,
)
from local_console.fastapi.routes.devices.configuration.dto import Status
from local_console.fastapi.routes.devices.configuration.dto import StatusType
from local_console.fastapi.routes.devices.dependencies import InjectDeviceController
from local_console.fastapi.routes.devices.dto import ConfigurationUpdateOutDTO
from local_console.fastapi.routes.devices.dto import DeviceListDTO
from local_console.fastapi.routes.devices.dto import DevicePostDTO
from local_console.fastapi.routes.devices.dto import PropertyInfo
from local_console.fastapi.routes.devices.dto import RPCRequestDTO
from local_console.fastapi.routes.devices.dto import RPCResponseDTO
from local_console.fastapi.routes.devices.dto import StateOutDTO
from pydantic import ValidationError

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("")
async def get_devices(
    controller: InjectDeviceController,
    connection_state: Annotated[
        ConnectionState | None,
        Query(
            description="Filter objects by their connection state. If not specified, devices with all connection states will be included."
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            description="Specify the maximum number of objects to return in a single call. This parameter is required. Default: 500",
            ge=1,
            le=1000,
        ),
    ] = 500,
    starting_after: Annotated[
        str | None,
        Query(
            description="Return objects strictly after the one identified by this value. Use it together with 'continuation_token' from previous calls in order to perform pagination."
        ),
    ] = None,
) -> DeviceListDTO:

    return controller.list_devices(
        length=limit,
        continuation_token=starting_after,
        connection_state=connection_state,
    )


@router.get(
    "/{device_id}",
    responses={
        404: {
            "model": ExternalDeviceNotFoundDocumentationMessage,
            "description": "Given device_id does not exist",
        }
    },
)
async def get_device(
    device_id: DeviceID, controller: InjectDeviceController
) -> DeviceStateInformation:
    return controller.get_device(device_id)


@router.post("")
async def create_device(
    controller: InjectDeviceController, device: DevicePostDTO
) -> EmptySuccess:
    return await controller.create(device)


@router.patch("/{device_id}")
def rename_device(
    device_id: DeviceID,
    new_name: str,
    controller: InjectDeviceController,
) -> EmptySuccess:
    return controller.rename_device(device_id, new_name)


@router.delete("/{device_id}")
async def delete_device(
    device_id: DeviceID, controller: InjectDeviceController
) -> EmptySuccess:
    return controller.delete(device_id)


@router.post(
    "/{device_id}/command",
    description="This endpoint allows users to execute predefined commands on the device, and provide the necessary arguments for their execution.",
    responses={
        404: {
            "model": ExternalDeviceNotFoundDocumentationMessage,
            "description": "Given device_id does not exist",
        }
    },
)
async def device_rpc(
    rpc_args: RPCRequestDTO,
    controller: InjectDeviceController,
    device_id: DeviceID,
) -> RPCResponseDTO:
    return await controller.rpc(device_id, "$system", rpc_args)


@router.post(
    "/{device_id}/modules/{module_id}/command",
    description="This endpoint allows users to execute predefined commands on the device, and provide the necessary arguments for their execution.",
    responses={
        404: {
            "model": ExternalDeviceNotFoundDocumentationMessage,
            "description": "Given device_id does not exist",
        }
    },
)
async def device_module_rpc(
    rpc_args: RPCRequestDTO,
    controller: InjectDeviceController,
    device_id: DeviceID,
    module_id: str,
) -> RPCResponseDTO:
    return await controller.rpc(device_id, module_id, rpc_args)


@router.patch("/{device_id}/property")
async def update_configuration(
    device_id: DeviceID,
    property_dto: PropertyInfo,
    controller: InjectDeviceController,
) -> ConfigurationUpdateOutDTO:
    await controller.configure(
        device_id=device_id,
        module_id="$system",
        property_info=property_dto,
    )
    return ConfigurationUpdateOutDTO(configuration=property_dto.configuration)


@router.patch("/{device_id}/modules/{module_id}/property")
async def update_module_configuration(
    device_id: DeviceID,
    module_id: str,
    property_dto: PropertyInfo,
    controller: InjectDeviceController,
) -> ConfigurationUpdateOutDTO:
    await controller.configure(
        device_id=device_id,
        module_id=module_id,
        property_info=property_dto,
    )
    return ConfigurationUpdateOutDTO(configuration=property_dto.configuration)


@router.get("/{device_id}/modules/{module_id}/property")
async def get_module_configuration(
    device_id: DeviceID,
    module_id: str,
    controller: InjectDeviceController,
) -> StateOutDTO:
    return await controller.get_configure(device_id=device_id, module_id=module_id)


@router.get("/{device_id}/configuration")
async def get_camera_configuration(
    device_id: DeviceID, controller: InjectCameraConfigurationController
) -> CameraConfigurationDTO:
    try:
        return controller.get_by_id(device_id)
    except (ValueError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid camera configuration data",
        ) from e


@router.patch("/{device_id}/configuration")
async def patch_camera_configuration(
    device_id: DeviceID,
    controller: InjectCameraConfigurationController,
    settings: CameraConfigurationDTO,
    dry_run: bool = False,
) -> CameraConfigurationDTO:
    error_status = {}
    try:
        if not dry_run:
            await controller.update(device_id, settings)
        else:
            error_status = controller.validate(device_id, settings)
    except UserException as e:
        if e.code == ErrorCodes.EXTERNAL_CANNOT_USE_DIRECTORY:
            error_status = {StatusType.FOLDER_ERROR: Status()}

    config = controller.get_by_id(device_id)
    config.status = error_status if dry_run else {**config.status, **error_status}

    return config
