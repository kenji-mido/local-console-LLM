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
from local_console.core.config import Config
from local_console.core.schemas.schemas import DeviceConnection
from local_console.core.schemas.schemas import DeviceListItem
from local_console.core.schemas.schemas import EVPParams
from local_console.core.schemas.schemas import GlobalConfiguration
from local_console.core.schemas.schemas import MQTTParams
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
    def __init__(self, host: str = "web.server", port: int = 80) -> None:
        self.host = host
        self.port = port

    def sample(self) -> WebserverParams:
        return WebserverParams(host=self.host, port=self.port)


class DeviceConnectionSampler:
    def __init__(
        self,
        name: str = random_alphanumeric(),
        mqtt_sampler: MQTTParamsSampler = MQTTParamsSampler(),
        web_sampler: WebserverParamsSampler = WebserverParamsSampler(),
    ) -> None:
        self.name = name
        self.mqtt = mqtt_sampler
        self.web = web_sampler

    def sample(self) -> DeviceConnection:
        return DeviceConnection(
            mqtt=self.mqtt.sample(), webserver=self.web.sample(), name=self.name
        )

    def list_of_samples(self, length: int = 10) -> list[DeviceConnection]:
        list_of_samples = [self.sample() for _ in range(length)]
        for index, dev in enumerate(list_of_samples):
            dev.name = f"{dev.name}_{index}"
            dev.mqtt.port = dev.mqtt.port + index
            dev.webserver.port = dev.webserver.port + index
        return list_of_samples


class EVPParamsSampler:
    def __init__(self, platform: str = "EVP1") -> None:
        self.platform = platform

    def sample(self) -> EVPParams:
        return EVPParams(iot_platform=self.platform)


class GlobalConfigurationSampler:
    def __init__(
        self,
        evp: EVPParamsSampler = EVPParamsSampler(),
        devices: DeviceConnectionSampler = DeviceConnectionSampler(),
        num_of_devices: int = 10,
    ) -> None:
        self.evp = evp
        self.devices = devices
        self.num_of_devices = num_of_devices

    def sample(self) -> GlobalConfiguration:
        devices = self.devices.list_of_samples(self.num_of_devices)
        return GlobalConfiguration(
            evp=self.evp.sample(), devices=devices, active_device=devices[0].mqtt.port
        )


class ConfigSampler:
    def __init__(self, config: GlobalConfigurationSampler) -> None:
        self.config = config

    def sample(self) -> Config:
        config = Config()
        config._config = self.config.sample()
        return config


class DeviceListItemSampler:
    def __init__(
        self,
        name: str = random_alphanumeric(),
        port: int = 1883 + random_int(max=100),
    ) -> None:
        self.name = name
        self.port = port

    def sample(self) -> DeviceListItem:
        return DeviceListItem(name=self.name, port=self.port)


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
