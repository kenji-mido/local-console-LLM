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
from local_console.clients.command.rpc_with_response import run_rpc_with_response
from local_console.core.camera.schemas import DeviceStateInformation
from local_console.core.config import Config
from local_console.core.device_services import DeviceServices
from local_console.fastapi.routes.commons import EmptySuccess
from local_console.fastapi.routes.devices.dto import DeviceListDTO
from local_console.fastapi.routes.devices.dto import DevicePostDTO
from local_console.fastapi.routes.devices.dto import PropertyInfo
from local_console.fastapi.routes.devices.dto import RPCRequestDTO
from local_console.fastapi.routes.devices.dto import RPCResponseDTO
from local_console.fastapi.routes.utils import schema_from_config
from local_console.utils.trio import lock_until_started


logger = logging.getLogger(__name__)


def direct_command_translator(command: str) -> str:
    if command == "direct_get_image":
        return "DirectGetImage"
    return command


class DevicesController:
    def __init__(self, config: Config, device_service: DeviceServices) -> None:
        self.config = config
        self.device_service = device_service

    def get_device(self, device_id: int) -> DeviceStateInformation:
        return self.device_service.get_device(device_id)

    def list_devices(
        self, length: int = 10, continuation_token: str | None = None
    ) -> DeviceListDTO:
        devices = self.device_service.list()

        return self._paginate(devices, length, continuation_token)

    async def create(self, device: DevicePostDTO) -> EmptySuccess:
        try:
            self.device_service.add_device(
                device.device_name,
                device.mqtt_port,
            )
            state = self.device_service.states[device.mqtt_port]
            await lock_until_started(lambda: state.mqtt_client_status)

        except TimeoutError as e:
            self.device_service.remove_device(device.mqtt_port)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not start server at port {device.mqtt_port}",
            ) from e

        return EmptySuccess()

    def delete(self, device_id: int) -> EmptySuccess:
        self.device_service.remove_device(device_id)
        return EmptySuccess()

    def rename_device(self, device_id: int, new_name: str) -> EmptySuccess:
        self.device_service.rename_device(device_id, new_name)
        return EmptySuccess()

    async def rpc(self, device_id: int, args: RPCRequestDTO) -> RPCResponseDTO:
        logger.debug(f"Rpc to device {device_id} has been requested")
        if device_id not in self.device_service.states:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find device {device_id}",
            )
        state = self.device_service.states[device_id]

        schema = schema_from_config(self.config.config)
        assert state.mqtt_client
        translated_command = direct_command_translator(args.command_name)
        result = await run_rpc_with_response(
            state,
            state.rpc_response,
            translated_command,
            args.parameters,
            schema,
        )
        lowerkeys = {
            key.lower(): value for key, value in result.payload["response"].items()
        }
        return RPCResponseDTO(command_response=lowerkeys)

    async def configure(
        self, device_id: int, module_id: str, property_info: PropertyInfo
    ) -> None:
        property_name, property_dict = property_info.get_property_name_and_values()

        if module_id == "$system":
            module_id = "backdoor-EA_Main"

        state = self.device_service.states[device_id]

        assert state.mqtt_client

        await state.mqtt_client.configure(
            module_id, property_name, json.dumps(property_dict)
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
