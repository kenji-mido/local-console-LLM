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
import logging

import trio
from local_console.core.camera.machine import Camera
from local_console.core.camera.qr.qr import QRService
from local_console.core.camera.schemas import assemble_device_state_info
from local_console.core.camera.schemas import DeviceStateInformation
from local_console.core.config import Config
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes
from local_console.core.schemas.schemas import DeviceConnection
from local_console.core.schemas.schemas import DeviceID
from local_console.core.schemas.schemas import DeviceListItem
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.servers.webserver import AsyncWebserver
from local_console.servers.webserver import FileInbox
from local_console.utils.local_network import is_port_open

logger = logging.getLogger(__name__)
config_obj = Config()

# Incoming images tend to be under 100 kB.
# Inference files are much smaller in most cases
MAX_INCOMING_SIZE: int = 500 * 1024


class DeviceServices:
    DEFAULT_DEVICE_NAME = "Default"
    DEFAULT_DEVICE_PORT = 1883
    DEFAULT_ONWIRE_SCHEMA = OnWireProtocol.EVP1

    def __init__(
        self,
        nursery: trio.Nursery,
        channel: trio.MemorySendChannel,
        webserver: AsyncWebserver,
        token: trio.lowlevel.TrioToken,
    ):
        self.nursery = nursery
        self.channel = channel
        self.token = token
        self.__cameras: dict[DeviceID, Camera] = {}
        self.webserver = webserver
        self.file_inbox = FileInbox(webserver)
        self.started = False
        self.qr = QRService()

    def __contains__(self, device_id: DeviceID) -> bool:
        return device_id in self.__cameras

    async def init_devices(self, device_configs: list[DeviceConnection]) -> None:
        """
        Initializes the devices based on the provided configuration list.
        If no devices are found, it creates a default device
        using the predefined default name and port. The default device is then
        added to the device manager, set as the active device, and the GUI proxy
        is switched to reflect this change.
        """
        if len(device_configs) == 0:
            # There should be at least one device
            default_device = self.default_device()
            await self.add_device(default_device.name, default_device.id)
            return

        for device in device_configs:
            await self.add_device_to_internals(device)

        self.started = True

    def get_device(self, device_id: DeviceID) -> DeviceStateInformation:
        for dev in config_obj.data.devices:
            dev_id = DeviceID(dev.id)
            if device_id != dev_id:
                continue
            camera = self.get_camera(dev_id)
            if not camera:
                logger.info(f"Device {dev_id} is in config but has no state")
            else:
                return assemble_device_state_info(
                    config_obj.get_device_config(device_id),
                    camera._common_properties.reported,
                    camera.connection_status,
                    camera.device_type,
                )
        raise UserException(
            code=ErrorCodes.EXTERNAL_DEVICE_NOT_FOUND,
            message=f"Device with id {device_id} not found.",
        )

    def list_devices(self) -> list[DeviceStateInformation]:
        devices: list[DeviceStateInformation] = []
        for device in config_obj.data.devices:
            camera = self.get_camera(device.id)
            if not camera:
                logger.warning(f"Camera instance with ID {device.id} was not found.")
                continue

            device_state_information = assemble_device_state_info(
                device,
                camera._common_properties.reported,
                camera.connection_status,
                camera.device_type,
            )
            devices.append(device_state_information)
        return devices

    def default_device(self) -> DeviceListItem:
        return DeviceListItem(
            name=self.DEFAULT_DEVICE_NAME,
            port=self.DEFAULT_DEVICE_PORT,
            id=DeviceID(self.DEFAULT_DEVICE_PORT),
            onwire_schema=self.DEFAULT_ONWIRE_SCHEMA,
        )

    async def add_device_to_internals(self, device: DeviceConnection) -> Camera:
        config_obj.commit_device_record(device)
        camera = Camera(
            device,
            self.channel.clone(),
            self.webserver,
            self.file_inbox,
            self.token,
            self.qr.persist_to,
        )

        auto_delete = config_obj.get_persistent_attr(device.id, "auto_deletion")
        if self.started:
            camera._common_properties.dirs_watcher.gather(auto_delete)

        config_obj.save_config()
        self.set_camera(device.id, camera)
        await self.nursery.start(camera.setup)

        return camera

    async def add_device(self, name: str, key: DeviceID) -> DeviceConnection:
        port = int(key)
        # Early validation via model instance creation
        device_connection = config_obj.construct_device_record(name, key)

        # Validation of other preconditions
        if self._is_name_already_used(name):
            raise UserException(
                ErrorCodes.EXTERNAL_DEVICE_NAMES_MUST_BE_UNIQUE,
                f'Device name "{name}" is already taken',
            )
        if self._is_port_already_used(port):
            raise UserException(
                ErrorCodes.EXTERNAL_DEVICE_PORTS_MUST_BE_UNIQUE,
                f"Specified port {port} is already taken",
            )
        if is_port_open(port):
            raise UserException(
                ErrorCodes.EXTERNAL_DEVICE_PORT_ALREADY_IN_USE,
                f"Specified MQTT port {port} is already in use. Please select another one",
            )

        await self.add_device_to_internals(device_connection)
        return device_connection

    def remove_device(self, device_id: DeviceID) -> None:
        camera = self.get_camera(device_id)
        if not camera:
            logger.warning(
                f"Device '{device_id}' was not registered, so it cannot be removed"
            )
            return

        if self.get_devices_count() <= 1:
            raise UserException(
                ErrorCodes.EXTERNAL_ONE_DEVICE_NEEDED,
                "You need at least one device to work with",
            )

        camera.shutdown()
        self.remove_camera(device_id)
        config_obj.remove_device(device_id)
        config_obj.save_config()

    def set_camera(self, device_id: DeviceID, state: Camera) -> None:
        self.__cameras[device_id] = state

    def get_camera(self, device_id: DeviceID) -> Camera | None:
        """
        Returns the current Camera for the specified device, or None if the
        device does not exist or has not yet been initialized
        """
        return self.__cameras.get(device_id, None)

    def get_cameras(self) -> list[Camera]:
        return list(self.__cameras.values())

    def remove_camera(self, device_id: DeviceID) -> None:
        if device_id in self.__cameras:
            del self.__cameras[device_id]

        self.file_inbox.reset_file_incoming_callable(device_id)

    def get_devices_count(self) -> int:
        return len(self.get_cameras())

    def shutdown(self) -> None:
        for camera in self.get_cameras():
            camera.shutdown()

    def rename_device(self, device_id: DeviceID, new_name: str) -> None:
        if self._is_name_already_used(new_name):
            raise UserException(
                ErrorCodes.EXTERNAL_DEVICE_NAMES_MUST_BE_UNIQUE,
                f'Device name "{new_name}" is already taken',
            )
        config_obj.rename_entry(device_id, new_name)

    def _is_name_already_used(self, device_name: str) -> bool:
        return any(d.name == device_name for d in config_obj.data.devices)

    def _is_port_already_used(self, device_port: int) -> bool:
        return any(d.mqtt.port == device_port for d in config_obj.data.devices)
