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
from local_console.core.enums import DEFAULT_PERSIST_SETTINGS
from local_console.core.schemas.schemas import DeviceConnection
from local_console.core.schemas.schemas import DeviceID
from local_console.core.schemas.schemas import DeviceListItem
from local_console.core.schemas.schemas import GlobalConfiguration
from local_console.core.schemas.schemas import LocalConsoleConfig
from local_console.core.schemas.schemas import MQTTParams
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.core.schemas.schemas import WebserverParams
from local_console.fastapi.routes.devices.dto import PropertyInfo

from tests.strategies.samplers.strings import random_alphanumeric
from tests.strategies.samplers.strings import random_int
from tests.strategies.samplers.strings import random_text


class MQTTParamsSampler:
    def __init__(
        self,
        host: str = "mqtt.server",
        port: int = 1883,
        device_id: str = random_text(),
    ) -> None:
        self.host = host
        self.port = port
        self.device_id = device_id

    def sample(self) -> MQTTParams:
        return MQTTParams(host=self.host, port=self.port, device_id=self.device_id)


class WebserverParamsSampler:
    def __init__(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        self.host = host
        self.port = port

    def sample(self) -> WebserverParams:
        return WebserverParams(host=self.host, port=self.port)


class OnWireProtocolSampler:
    def __init__(self, protocol: OnWireProtocol = OnWireProtocol.EVP1) -> None:
        self.protocol = protocol

    def sample(self) -> OnWireProtocol:
        return self.protocol


class DeviceConnectionSampler:
    def __init__(
        self,
        name: str = random_alphanumeric(),
        mqtt_sampler: MQTTParamsSampler = MQTTParamsSampler(),
        ows_sampler: OnWireProtocolSampler = OnWireProtocolSampler(),
    ) -> None:
        self.name = name
        self.mqtt = mqtt_sampler
        self.ows = ows_sampler

    def sample(self) -> DeviceConnection:
        return DeviceConnection(
            mqtt=self.mqtt.sample(),
            name=self.name,
            id=DeviceID(self.mqtt.port),
            persist=DEFAULT_PERSIST_SETTINGS.model_copy(),
            onwire_schema=self.ows.sample(),
        )

    def list_of_samples(self, length: int = 10) -> list[DeviceConnection]:
        list_of_samples = [self.sample() for _ in range(length)]
        for index, dev in enumerate(list_of_samples):
            dev.name = f"{dev.name}_{index}"
            mqtt_port = dev.mqtt.port + index
            dev.mqtt.port = mqtt_port
            dev.id = DeviceID(mqtt_port)
        return list_of_samples


class GlobalConfigurationSampler:
    def __init__(
        self,
        devices: DeviceConnectionSampler = DeviceConnectionSampler(),
        web_sampler: WebserverParamsSampler = WebserverParamsSampler(),
        num_of_devices: int = 10,
    ) -> None:
        self.devices = devices
        self.web = web_sampler
        self.num_of_devices = num_of_devices

    def sample(self) -> GlobalConfiguration:
        devices = self.devices.list_of_samples(self.num_of_devices)
        lc_conf = LocalConsoleConfig(webserver=self.web.sample())
        return GlobalConfiguration(devices=devices, config=lc_conf)


class DeviceListItemSampler:
    def __init__(
        self,
        name: str = random_alphanumeric(),
        port: int = 1883 + random_int(min=1, max=100),
        onwire_schema: OnWireProtocol = OnWireProtocol.EVP1,
    ) -> None:
        self.name = name
        self.port = port
        self.onwire_schema = onwire_schema

    def sample(self) -> DeviceListItem:
        return DeviceListItem(
            name=self.name,
            port=self.port,
            id=DeviceID(self.port),
            onwire_schema=self.onwire_schema,
        )


class PropertySampler:
    def __init__(
        self,
        property_name: str = "property_name_42",
        property_key: str = "property_key_42",
        property_value: str = "property_value_42",
    ):
        self.property_name = property_name
        self.property_key = property_key
        self.property_value = property_value

    def sample(self) -> PropertyInfo:
        return PropertyInfo(
            configuration={self.property_name: {self.property_key: self.property_value}}
        )
