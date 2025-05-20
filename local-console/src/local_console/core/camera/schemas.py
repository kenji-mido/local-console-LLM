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
from local_console.core.camera.enums import ConnectionState
from local_console.core.camera.qr.schema import QRInfo
from local_console.core.commands.deploy import DeploymentSpec
from local_console.core.schemas.schemas import DeviceConnection
from local_console.core.schemas.schemas import DeviceType
from pydantic import BaseModel
from pydantic import field_validator


class MSInfo(BaseModel):
    name: str | None = None
    firmware_version: str
    loader_version: str | None = None


class MSAIModel(BaseModel):
    name: str | None = None
    version: str | None = None
    converter_version: str | None = None


class MSDeviceInfo(BaseModel):
    processors: list[MSInfo] | None = None
    sensors: list[MSInfo] | None = None
    ai_models: list[MSAIModel] | None = None


class MSDeviceState(BaseModel):
    process_state: str | None = None

    @field_validator("process_state")
    @classmethod
    def validate_process_state_value(cls, v: str) -> str:
        valid_states = {
            None,
            "Idle",
            "Aborted",
            "InstallationMode",
            "PowerSaving",
            "FactoryReset",
            "FactoryResetDone",
        }
        if v not in valid_states:
            raise ValueError(
                f"Given state {v} is not a valid one. Please choose one from: {valid_states}"
            )
        return v


class MSPeriodicSetting(BaseModel):
    ip_addr_setting: str | None = None

    @field_validator("ip_addr_setting")
    @classmethod
    def validate_ip_addr_setting(cls, v: str) -> str:
        valid_ip_addr_setting = {
            None,
            "save",
            "dhcp",
        }
        if v not in valid_ip_addr_setting:
            raise ValueError(
                f"Given ip_addr_setting {v} is not a valid one. Please choose one from: {valid_ip_addr_setting}"
            )
        return v


class MSNetworkSettings(BaseModel):
    ntp_url: str | None = None
    gateway_address: str | None = None
    subnet_mask: str | None = None
    ip_address: str | None = None
    dns_address: str | None = None
    proxy_url: str | None = None
    proxy_port: int | None = None
    proxy_user_name: str | None = None


class MSSSIDSetting(BaseModel):
    ssid: str | None = None
    password: str | None = None


class MSWirelessSetting(BaseModel):
    sta_mode_setting: MSSSIDSetting = MSSSIDSetting()
    ap_mode_setting: MSSSIDSetting = MSSSIDSetting()


class MSPrivateEndpointSettings(BaseModel):
    endpoint_url: str | None = None
    endpoint_port: int | None = None


class MState(BaseModel):
    wireless_setting: MSWirelessSetting = MSWirelessSetting()
    PRIVATE_endpoint_settings: MSPrivateEndpointSettings = MSPrivateEndpointSettings()


class MConfig(BaseModel):
    periodic_setting: MSPeriodicSetting = MSPeriodicSetting()
    device_info: MSDeviceInfo = MSDeviceInfo()
    device_state: MSDeviceState = MSDeviceState()
    network_settings: MSNetworkSettings = MSNetworkSettings()


class MProperty(BaseModel):
    state: MState = MState()
    configuration: MConfig = MConfig()


class ModuleInfo(BaseModel):
    module_id: str = "$system"
    property: MProperty = MProperty()


class DeviceStateInformation(BaseModel):
    device_name: str
    device_type: str | None
    device_id: str
    description: str
    internal_device_id: str
    connection_state: ConnectionState
    inactivity_timeout: int = 0
    modules: list[ModuleInfo] | None = None


class PropertiesReport(BaseModel):
    """
    This model holds the value of various properties reported
    by the camera firmware which are of interest for operations
    on a camera. It is aimed as a schema-agnostic parameter store.
    """

    # v1:DeviceConfiguration.Version.ApFwVersion
    # v2:EdgeSystemCommon | jq '.["state/$system/device_info"].chips | .[] | select(.name == "main_chip") | .firmware_version'
    cam_fw_version: str | None = None

    # v1:DeviceConfiguration.Version.SensorFwVersion
    # v2:EdgeSystemCommon | jq '.["state/$system/device_info"].chips | .[] | select(.name == "sensor_chip") | .firmware_version'
    sensor_fw_version: str | None = None

    # v1:DeviceConfiguration.OTA.UpdateStatus
    # v2:EdgeSystemCommon | jq '.["state/$system/PRIVATE_deploy_firmware"].targets | .[] | select(.chip == "sensor_chip") | .process_state'
    sensor_fw_ota_status: str | None = None

    # v1:DeviceConfiguration.Version.SensorLoaderVersion
    # v2:EdgeSystemCommon | jq '.["state/$system/device_info"].chips | .[] | select(.name == "sensor_chip") | .loader_version'
    sensor_loader_version: str | None = None

    # v1:DeviceConfiguration.Hardware.Sensor
    # v2:EdgeSystemCommon | jq '.["state/$system/device_info"].chips | .[] | select(.name == "sensor_chip") | .hardware_version' or maybe .id instead
    sensor_hardware: str | None = None

    # v1:DeviceConfiguration.Status.Sensor
    # v2: No longer available to the "system app". Only available to edge apps via some C API.
    sensor_status: str | None = None

    # v1:DeviceConfiguration.Version.DnnModelVersion
    # v2:EdgeSystemCommon | jq '.["state/$system/device_info"].chips | .[] | select(.name == "sensor_chip") | .ai_models | .[] | .version'
    dnn_versions: list[str] | None = None

    # v1:DeviceConfiguration.OTA.UpdateStatus
    # v2:EdgeSystemCommon | jq '.["state/$system/PRIVATE_deploy_firmware"].targets | .[] | select(.chip == "main_chip") | .process_state'
    cam_fw_ota_status: str | None = None

    # v1:DeviceConfiguration.Status.ApplicationProcessor
    # v2:EdgeSystemCommon | jq '.["state/$system/device_states"].process_state'
    cam_fw_status: str | None = None

    # v1:DeviceConfiguration.Network.ProxyPort
    # v2:EdgeSystemCommon | jq '.["state/$system/network_settings"].proxy_settings.proxy_port'
    proxy_port: int | None = None

    # v1:DeviceConfiguration.Network.ProxyUserName
    # v2:EdgeSystemCommon | jq '.["state/$system/network_settings"].proxy_settings.proxy_user_name'
    proxy_user_name: str | None = None

    # v1:DeviceConfiguration.Network.ProxyURL
    # v2:EdgeSystemCommon | jq '.["state/$system/network_settings"].proxy_settings.proxy_url'
    proxy_url: str | None = None

    # v1:DeviceConfiguration.Network.NTP
    # v2:EdgeSystemCommon | jq '.["state/$system/network_settings"].ntp_url'
    ntp_url: str | None = None

    # v1:DeviceConfiguration.Network.Gateway
    # v2:EdgeSystemCommon | jq '.["state/$system/network_settings"].static_settings_ipv4.gateway_address'
    gateway_address: str | None = None

    # v1:DeviceConfiguration.Network.SubnetMask
    # v2:EdgeSystemCommon | jq '.["state/$system/network_settings"].static_settings_ipv4.subnet_mask'
    subnet_mask: str | None = None

    # v1:DeviceConfiguration.Network.IPAddress
    # v2:EdgeSystemCommon | jq '.["state/$system/network_settings"].static_settings_ipv4.ip_address'
    ip_address: str | None = None

    # v1:DeviceConfiguration.Network.DNS
    # v2:EdgeSystemCommon | jq '.["state/$system/network_settings"].static_settings_ipv4.dns_address'
    dns_address: str | None = None

    # Attributes not reported by the device

    # v2: "state/X/edge_app" is mapped as {"X": value}
    edge_app: dict = {}
    # v2: latest Edge App deployment. Used to re-deploy Edge App when doing AI Model OTA
    _latest_deployment_spec: DeploymentSpec | None = None
    # v2: latest Edge App configuration
    latest_edge_app_config: dict = {}

    @property
    def latest_deployment_spec(self) -> DeploymentSpec | None:
        return (
            self._latest_deployment_spec.model_copy(deep=True)
            if self._latest_deployment_spec
            else None
        )

    @latest_deployment_spec.setter
    def latest_deployment_spec(self, value: DeploymentSpec | None) -> None:
        self._latest_deployment_spec = value.model_copy(deep=True) if value else None

    def is_empty(self) -> bool:
        some_is_set = any(
            bool(val) for val in self.model_dump(exclude_defaults=True).values()
        )
        return not some_is_set


def assemble_device_state_info(
    device_connection: DeviceConnection,
    properties: PropertiesReport,
    conn_state: ConnectionState,
    device_type: DeviceType | None,
) -> DeviceStateInformation:
    modules = [ModuleInfo()]
    state: MState = modules[0].property.state
    config: MConfig = modules[0].property.configuration
    enrich_with_device_connection(state, device_connection)

    populate_from_properties(config, properties)
    add_network_info_from_status(config, properties)
    add_missing_network_info(config, device_connection.qr)

    return DeviceStateInformation(
        device_name=device_connection.name,
        device_type=device_type,
        device_id=str(device_connection.id),
        internal_device_id=str(device_connection.id),
        description=device_connection.name,
        modules=modules,
        connection_state=conn_state,
    )


def ip_address_to_ip_addr_setting(ip_address: str | None) -> str:
    return "save" if ip_address else "dhcp"


def get_model_info_from_dnn_model(dnn_model: str) -> tuple[str, str, str]:
    converter_version = dnn_model[:6]
    network_id = dnn_model[6:12]
    model_version = dnn_model[12:]
    return network_id, model_version, converter_version


def enrich_with_device_connection(
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


def populate_from_properties(config: MConfig, properties: PropertiesReport) -> None:
    if properties.cam_fw_version:
        config.device_info.processors = [
            MSInfo(firmware_version=properties.cam_fw_version)
        ]
    if properties.sensor_fw_version:
        loader_version = properties.sensor_loader_version
        config.device_info.sensors = [
            MSInfo(
                name=properties.sensor_hardware,
                firmware_version=properties.sensor_fw_version,
                loader_version=loader_version,
            )
        ]

    config.device_state.process_state = properties.cam_fw_status
    config.device_info.ai_models = []
    if properties.dnn_versions is None:
        return
    for dnn_model in properties.dnn_versions:
        network_id, model_version, converter_version = get_model_info_from_dnn_model(
            dnn_model
        )
        config.device_info.ai_models.append(
            MSAIModel(
                name=network_id,
                version=model_version,
                converter_version=converter_version,
            )
        )


def add_network_info_from_status(config: MConfig, properties: PropertiesReport) -> None:

    port = properties.proxy_port
    config.network_settings.proxy_port = (
        None if port is None else (properties.proxy_port if 0 < port < 65536 else None)
    )

    config.network_settings.proxy_user_name = properties.proxy_user_name
    config.network_settings.proxy_url = properties.proxy_url
    config.network_settings.ntp_url = properties.ntp_url
    config.network_settings.gateway_address = properties.gateway_address
    config.network_settings.subnet_mask = properties.subnet_mask
    config.network_settings.ip_address = properties.ip_address
    config.network_settings.dns_address = properties.dns_address


def add_missing_network_info(config: MConfig, qr: QRInfo | None) -> None:
    network = config.network_settings
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

    config.periodic_setting.ip_addr_setting = ip_address_to_ip_addr_setting(
        network.ip_address
    )
