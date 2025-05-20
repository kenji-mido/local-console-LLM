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
import base64
import json
import logging

from fastapi import HTTPException
from fastapi import status
from local_console.core.camera.enums import ConnectionState
from local_console.core.camera.schemas import DeviceStateInformation
from local_console.core.commands.rpc_with_response import DirectCommandStatus
from local_console.core.config import Config
from local_console.core.device_services import DeviceServices
from local_console.core.error.base import UserException
from local_console.core.schemas.schemas import DeviceID
from local_console.fastapi.routes.commons import EmptySuccess
from local_console.fastapi.routes.devices.dto import DeviceListDTO
from local_console.fastapi.routes.devices.dto import DevicePostDTO
from local_console.fastapi.routes.devices.dto import PropertyInfo
from local_console.fastapi.routes.devices.dto import RPCRequestDTO
from local_console.fastapi.routes.devices.dto import RPCResponseDTO
from local_console.fastapi.routes.devices.dto import RPCResponseResult
from local_console.fastapi.routes.devices.dto import StateOutDTO


logger = logging.getLogger(__name__)


class DevicesController:
    def __init__(self, config: Config, device_service: DeviceServices) -> None:
        self.config = config
        self.device_service = device_service

    def get_device(self, key: DeviceID) -> DeviceStateInformation:
        return self.device_service.get_device(key)

    def list_devices(
        self,
        length: int = 10,
        continuation_token: str | None = None,
        connection_state: ConnectionState | None = None,
    ) -> DeviceListDTO:
        devices = self.device_service.list_devices()
        if connection_state:
            devices = [
                device
                for device in devices
                if device.connection_state == connection_state
            ]
        return self._paginate(devices, length, continuation_token)

    async def create(self, device: DevicePostDTO) -> EmptySuccess:
        try:
            await self.device_service.add_device(
                device.device_name,
                device.id,
            )
        except* UserException as e:
            raise e.exceptions[0]
        except* Exception as e:
            self.device_service.remove_device(device.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not start server at port {device.id}",
            ) from e.exceptions[0]

        return EmptySuccess()

    def delete(self, device_id: DeviceID) -> EmptySuccess:
        self.device_service.remove_device(device_id)
        return EmptySuccess()

    def rename_device(self, device_id: DeviceID, new_name: str) -> EmptySuccess:
        self.device_service.rename_device(device_id, new_name)
        return EmptySuccess()

    async def rpc(
        self, device_id: DeviceID, module_id: str, args: RPCRequestDTO
    ) -> RPCResponseDTO:
        logger.debug(f"RPC to device {module_id} from {device_id} has been requested")
        camera = self.device_service.get_camera(device_id)
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find device {device_id}",
            )

        res = await camera.run_command(
            module_id,
            args.command_name,
            args.parameters,
            args.extra or {},
        )
        result = RPCResponseResult.ERROR
        command_response = None
        if res:
            body = res.direct_command_response
            if body.status == DirectCommandStatus.OK:
                result = RPCResponseResult.SUCCESS
                if body.response:
                    command_response = json.loads(body.response)

        return RPCResponseDTO(result=result, command_response=command_response)

    async def configure(
        self, device_id: DeviceID, module_id: str, property_info: PropertyInfo
    ) -> None:
        camera = self.device_service.get_camera(device_id)
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find device {device_id}",
            )

        property_name, property_dict = property_info.get_property_name_and_values()
        await camera.send_configuration(
            module_id,
            property_name,
            property_dict,
        )

    async def get_configure(self, device_id: DeviceID, module_id: str) -> StateOutDTO:
        camera = self.device_service.get_camera(device_id)
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find device {device_id}",
            )
        return StateOutDTO(
            state=(
                {"edge_app": camera._common_properties.reported.edge_app[module_id]}
                if module_id in camera._common_properties.reported.edge_app
                else {}
            )
        )

    def _paginate(
        self,
        devices: list[DeviceStateInformation],
        length: int = 10,
        continuation_token: str | None = None,
    ) -> DeviceListDTO:
        continuation_index = self._pagination_index(devices, continuation_token)
        ending_index = continuation_index + length
        paginated_devices = devices[continuation_index:ending_index]
        continuation_token = ""
        if len(devices) > ending_index:
            next_device = devices[ending_index]
            continuation_token = base64.b64encode(
                next_device.device_id.encode("utf-8")
            ).decode("utf-8")
        return DeviceListDTO(
            devices=paginated_devices, continuation_token=continuation_token
        )

    def _pagination_index(
        self,
        devices: list[DeviceStateInformation],
        continuation_token: str | None = None,
    ) -> int:
        if continuation_token:
            continuation_decoded = base64.b64decode(
                continuation_token.encode("utf-8")
            ).decode("utf-8")
            for index, device in enumerate(devices):
                if device.device_id == continuation_decoded:
                    return index
            logger.warning(f"invalid continuation token {continuation_token}")
        return 0
