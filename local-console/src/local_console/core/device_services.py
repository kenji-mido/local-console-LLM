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
from functools import partial
from pathlib import Path
from typing import Any
from typing import Callable

import trio
from local_console.core.camera.enums import ConnectionState
from local_console.core.camera.mixin_streaming import default_process_camera_upload
from local_console.core.camera.mixin_streaming import StreamingMixin
from local_console.core.camera.qr.qr import QRService
from local_console.core.camera.qr.schema import QRInfo
from local_console.core.camera.schemas import DeviceStateInformation
from local_console.core.camera.schemas import ModuleInfo
from local_console.core.camera.schemas import MSAIModel
from local_console.core.camera.schemas import MSInfo
from local_console.core.camera.schemas import MState
from local_console.core.camera.state import CameraState
from local_console.core.config import config_obj
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.core.schemas.schemas import DeviceConnection
from local_console.core.schemas.schemas import DeviceListItem
from local_console.utils.local_network import is_port_open


logger = logging.getLogger(__name__)


def _ip_address_to_ip_addr_setting(ip_address: str | None) -> str:
    return "save" if ip_address else "dhcp"


def get_model_info_from_dnn_model(dnn_model: str) -> tuple[str, str, str]:
    converter_version = dnn_model[:6]
    network_id = dnn_model[6:12]
    model_version = dnn_model[12:]
    return network_id, model_version, converter_version


def _enrich_with_device_connection(
    state: MState, device_connection: DeviceConnection
) -> None:
    state.PRIVATE_endpoint_settings.endpoint_url = device_connection.mqtt.host
    state.PRIVATE_endpoint_settings.endpoint_port = device_connection.mqtt.port

    if device_connection.qr and device_connection.qr.mqtt_host:
        # Latest QR generated for the device before the device connected the first time
        state.PRIVATE_endpoint_settings.endpoint_url = device_connection.qr.mqtt_host
    if device_connection.qr and device_connection.qr.wifi_ssid:
        state.wireless_setting.sta_mode_setting.ssid = device_connection.qr.wifi_ssid
    if device_connection.qr and device_connection.qr.wifi_pass:
        state.wireless_setting.sta_mode_setting.password = (
            device_connection.qr.wifi_pass
        )


def _enrich_with_device_config(
    state: MState, device_config: DeviceConfiguration
) -> None:
    if device_config.Version.ApFwVersion:
        state.device_info.processors = [
            MSInfo(firmware_version=device_config.Version.ApFwVersion)
        ]
    if device_config.Version.SensorFwVersion:
        loader_version = device_config.Version.SensorLoaderVersion
        state.device_info.sensors = [
            MSInfo(
                name=device_config.Hardware.Sensor,
                firmware_version=device_config.Version.SensorFwVersion,
                loader_version=loader_version,
            )
        ]
    if device_config.Version.ApFwVersion:
        state.device_info.processors = [
            MSInfo(firmware_version=device_config.Version.ApFwVersion)
        ]
    if device_config.Version.SensorFwVersion:
        loader_version = device_config.Version.SensorLoaderVersion
        state.device_info.sensors = [
            MSInfo(
                name=device_config.Hardware.Sensor,
                firmware_version=device_config.Version.SensorFwVersion,
                loader_version=loader_version,
            )
        ]

    state.device_state.process_state = device_config.Status.ApplicationProcessor

    state.network_settings.proxy_port = (
        device_config.Network.ProxyPort if device_config.Network else None
    )

    state.network_settings.proxy_user_name = (
        device_config.Network.ProxyUserName if device_config.Network else ""
    )
    state.network_settings.proxy_url = (
        device_config.Network.ProxyURL if device_config.Network else ""
    )
    state.device_info.ai_models = []
    for dnn_model in device_config.Version.DnnModelVersion:
        network_id, model_version, converter_version = get_model_info_from_dnn_model(
            dnn_model
        )
        state.device_info.ai_models.append(
            MSAIModel(
                name=network_id,
                version=model_version,
                converter_version=converter_version,
            )
        )


def _add_network_info_from_status(
    state: MState, device_config: DeviceConfiguration
) -> None:
    if not device_config.Network:
        return

    state.network_settings.ntp_url = device_config.Network.NTP
    state.network_settings.gateway_address = device_config.Network.Gateway
    state.network_settings.subnet_mask = device_config.Network.SubnetMask
    state.network_settings.ip_address = device_config.Network.IPAddress
    state.network_settings.dns_address = device_config.Network.DNS


def _add_missing_network_info(state: MState, qr: QRInfo | None) -> None:
    network = state.network_settings
    if qr:
        network.ntp_url = qr.ntp if not network.ntp_url else network.ntp_url
        network.gateway_address = (
            qr.gateway if not network.gateway_address else network.gateway_address
        )
        network.subnet_mask = (
            qr.subnet_mask if not network.subnet_mask else network.subnet_mask
        )
        network.ip_address = (
            qr.ip_address if not network.ip_address else network.ip_address
        )
        network.dns_address = qr.dns if not network.dns_address else network.dns_address

    state.periodic_setting.ip_addr_setting = _ip_address_to_ip_addr_setting(
        network.ip_address
    )


def device_to_dto(
    device_connection: DeviceConnection,
    device_config: DeviceConfiguration | None,
    conn_state: ConnectionState,
) -> DeviceStateInformation:
    modules = [ModuleInfo()]
    state = modules[0].property.state
    _enrich_with_device_connection(state, device_connection)

    if device_config:
        _enrich_with_device_config(state, device_config)
        _add_network_info_from_status(state, device_config)
    _add_missing_network_info(state, device_connection.qr)

    return DeviceStateInformation(
        device_name=device_connection.name,
        device_id=str(device_connection.mqtt.port),
        internal_device_id=str(device_connection.mqtt.port),
        description=device_connection.name,
        port=device_connection.mqtt.port,
        modules=modules,
        connection_state=conn_state,
    )


class DeviceServices:
    _STATE_TO_PROXY_PROPS: dict[str, Callable[[Any], Any]] = {
        "module_file": lambda x: x,
        "ai_model_file": lambda x: x,
        "size": int,
        "unit": lambda x: x,
        "vapp_type": lambda x: x,
        "vapp_schema_file": lambda x: x,
        "vapp_config_file": lambda x: x,
        "vapp_labels_file": lambda x: x,
        "image_dir_path": Path,
        "inference_dir_path": Path,
    }
    DEFAULT_DEVICE_NAME = "Default"
    DEFAULT_DEVICE_PORT = 1883

    def __init__(
        self,
        nursery: trio.Nursery,
        channel: trio.MemorySendChannel,
        token: trio.lowlevel.TrioToken,
        process_camera_upload: Callable[
            [StreamingMixin, bytes, str], None
        ] = default_process_camera_upload,
    ):
        self.process_camera_upload = process_camera_upload
        self.nursery = nursery
        self.channel = channel
        self.token = token
        self.states: dict[int, CameraState] = {}
        self.started = False
        self.qr = QRService()

    def init_devices(self, device_configs: list[DeviceConnection]) -> None:
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
            self.add_device(default_device.name, default_device.port)
            return

        for device in device_configs:
            self.add_device_to_internals(device)

        self.started = True

    def get_device(self, device_id: int) -> DeviceStateInformation:
        for device in config_obj.config.devices:
            device_port = device.mqtt.port
            if device_id != device_port:
                continue
            device_state = self.get_state(device_port)
            if not device_state:
                logger.info(f"Device {device_port} is in config but has no state")
            else:
                return device_to_dto(
                    config_obj.get_device_config(device_id),
                    device_state.device_config.value,
                    device_state.connection_status,
                )
        raise UserException(
            code=ErrorCodes.EXTERNAL_DEVICE_NOT_FOUND,
            message=f"Device with id {device_id} not found.",
        )

    def list(self) -> list[DeviceStateInformation]:
        devices: list[DeviceStateInformation] = []
        for device in config_obj.config.devices:
            device_state = self.states[device.mqtt.port]
            device_config = device_state.device_config
            device_state_information = device_to_dto(
                device, device_config.value, device_state.connection_status
            )
            devices.append(device_state_information)
        return devices

    def default_device(self) -> DeviceListItem:
        return DeviceListItem(
            name=self.DEFAULT_DEVICE_NAME, port=self.DEFAULT_DEVICE_PORT
        )

    def add_device_to_internals(self, device: DeviceConnection) -> CameraState:
        config = config_obj.get_config()
        config_obj.commit_device_record(device)

        state = CameraState(
            self.channel.clone(), self.token, self.process_camera_upload
        )
        self.states[device.mqtt.port] = state
        state.initialize_connection_variables(config.evp.iot_platform, device)
        self.initialize_persistency(device.mqtt.port)
        self.nursery.start_soon(state.startup, device.mqtt.port)
        config_obj.save_config()

        state.device_config.subscribe(partial(self.qr.persist_to, device.mqtt.port))

        return state

    def add_device(self, name: str, port: int) -> DeviceConnection:
        # Early validation via model instance creation
        device_connection = config_obj.construct_device_record(name, port)

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

        self.add_device_to_internals(device_connection)
        return device_connection

    def remove_device(self, port: int) -> None:
        if port not in self.states:
            logger.warning(
                f"Device '{port}' was not registered, so it cannot be removed"
            )
            return

        if len(self.states) <= 1:
            raise UserException(
                ErrorCodes.EXTERNAL_ONE_DEVICE_NEEDED,
                "You need at least one device to work with",
            )

        self.states[port].shutdown()
        del self.states[port]
        config_obj.remove_device(port)
        config_obj.save_config()

    def update_ip_address(self, port: int, new_ip: str) -> None:
        config_obj.update_ip_address(port, new_ip)
        config_obj.save_config()

    def get_state(self, port: int) -> CameraState | None:
        if port not in self.states:
            return None
        return self.states[port]

    def shutdown(self) -> None:
        for state in self.states.values():
            state.shutdown()

    def rename_device(self, device_id: int, new_name: str) -> None:
        if self._is_name_already_used(new_name):
            raise UserException(
                ErrorCodes.EXTERNAL_DEVICE_NAMES_MUST_BE_UNIQUE,
                f'Device name "{new_name}" is already taken',
            )
        config_obj.rename_entry(device_id, new_name)

    def _is_name_already_used(self, device_name: str) -> bool:
        return any(d.name == device_name for d in config_obj.config.devices)

    def _is_port_already_used(self, device_port: int) -> bool:
        return any(d.mqtt.port == device_port for d in config_obj.config.devices)

    def _register_persistency(self, device_port: int) -> None:
        """
        Registers persistency for state attributes of a device. When the state
        attributes change, their new values are saved to the persistent configuration.
        """

        def save_configuration(attribute: str, current: Any, previous: Any) -> None:
            persist = config_obj.get_device_config(device_port).persist
            for item in self._STATE_TO_PROXY_PROPS.keys():
                if attribute == item:
                    setattr(persist, item, str(current))

            # Save to disk
            config_obj.save_config()

        state = self.get_state(device_port)
        # Save configuration for any modification of relevant variables
        for item in self._STATE_TO_PROXY_PROPS:
            getattr(state, item).subscribe(partial(save_configuration, item))

    def _update_from_persistency(self, device_port: int) -> None:
        """
        Update attributes of the device's state and proxies from persistent configuration.
        """
        persist = config_obj.get_device_config(device_port).persist
        state = self.get_state(device_port)
        assert persist

        # Attributes with `bind_state_to_proxy` requires to update using `.value` to trigger the binding
        for item, cast_func in self._STATE_TO_PROXY_PROPS.items():
            if getattr(persist, item):
                setattr(
                    getattr(state, item),
                    "value",
                    cast_func(getattr(persist, item)),
                )

    def initialize_persistency(self, device_port: int) -> None:
        self._register_persistency(device_port)
        self._update_from_persistency(device_port)
