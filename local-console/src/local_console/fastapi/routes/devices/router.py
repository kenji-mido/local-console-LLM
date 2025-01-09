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
from fastapi import HTTPException
from fastapi import status
from local_console.core.camera.schemas import DeviceStateInformation
from local_console.fastapi.routes.commons import EmptySuccess
from local_console.fastapi.routes.devices.configuration.dependencies import (
    InjectCameraConfigurationController,
)
from local_console.fastapi.routes.devices.configuration.dto import (
    CameraConfigurationDTO,
)
from local_console.fastapi.routes.devices.dependencies import InjectDeviceController
from local_console.fastapi.routes.devices.dto import ConfigurationUpdateInDTO
from local_console.fastapi.routes.devices.dto import ConfigurationUpdateOutDTO
from local_console.fastapi.routes.devices.dto import DeviceListDTO
from local_console.fastapi.routes.devices.dto import DevicePostDTO
from local_console.fastapi.routes.devices.dto import RPCRequestDTO
from local_console.fastapi.routes.devices.dto import RPCResponseDTO
from pydantic import ValidationError

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("")
async def get_devices(
    controller: InjectDeviceController,
    limit: int = 1000,
    continuation_token: str | None = None,
) -> DeviceListDTO:
    return controller.list_devices(limit, continuation_token)


@router.get("/{device_id}")
async def get_device(
    device_id: int, controller: InjectDeviceController
) -> DeviceStateInformation:
    return controller.get_device(device_id)


@router.post("")
async def create_device(
    controller: InjectDeviceController, device: DevicePostDTO
) -> EmptySuccess:
    return await controller.create(device)


@router.patch("/{device_id}")
def rename_device(
    device_id: int,
    new_name: str,
    controller: InjectDeviceController,
) -> EmptySuccess:
    return controller.rename_device(device_id, new_name)


@router.delete("/{device_id}")
async def delete_device(
    device_id: int, controller: InjectDeviceController
) -> EmptySuccess:
    return controller.delete(device_id)


@router.post("/{device_id}/modules/$system/command")
async def device_rpc(
    device_id: int, rpc_args: RPCRequestDTO, controller: InjectDeviceController
) -> RPCResponseDTO:
    return await controller.rpc(device_id, rpc_args)


@router.patch("/{device_id}/modules/{module_id}")
async def update_module_configuration(
    device_id: int,
    module_id: str,
    configuration_update_dto: ConfigurationUpdateInDTO,
    controller: InjectDeviceController,
) -> ConfigurationUpdateOutDTO:
    await controller.configure(
        device_id=device_id,
        module_id=module_id,
        property_info=configuration_update_dto.property,
    )
    return ConfigurationUpdateOutDTO(property=configuration_update_dto.property)


@router.get("/{device_id}/configuration")
async def get_camera_configuration(
    device_id: int, controller: InjectCameraConfigurationController
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
    device_id: int,
    controller: InjectCameraConfigurationController,
    settings: CameraConfigurationDTO,
) -> EmptySuccess:
    return await controller.update(device_id, settings)
