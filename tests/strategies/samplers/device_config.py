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
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.core.schemas.edge_cloud_if_v1 import DnnModelVersion
from local_console.core.schemas.edge_cloud_if_v1 import Hardware
from local_console.core.schemas.edge_cloud_if_v1 import Network
from local_console.core.schemas.edge_cloud_if_v1 import OTA
from local_console.core.schemas.edge_cloud_if_v1 import Permission
from local_console.core.schemas.edge_cloud_if_v1 import Status
from local_console.core.schemas.edge_cloud_if_v1 import Version


class NetworkSampler:
    def __init__(
        self,
        proxy_url: str = "192.168.1.1",
        proxy_port: int = 1883,
        proxy_username: str = "username_42",
        ip_address: str = "192.168.1.2",
        subnet_mask: str = "255.255.255.0",
        gateway: str = "192.168.1.3",
        dns: str = "8.8.8.8",
        ntp: str = "192.168.1.4",
    ):
        self.proxy_url = proxy_url
        self.proxy_port = proxy_port
        self.proxy_username = proxy_username
        self.ip_address = ip_address
        self.subnet_mask = subnet_mask
        self.gateway = gateway
        self.dns = dns
        self.ntp = ntp

    def sample(self) -> Network:
        return Network(
            ProxyURL=self.proxy_url,
            ProxyPort=self.proxy_port,
            ProxyUserName=self.proxy_username,
            IPAddress=self.ip_address,
            SubnetMask=self.subnet_mask,
            Gateway=self.gateway,
            DNS=self.dns,
            NTP=self.ntp,
        )


class HardwareSampler:
    def __init__(
        self,
        sensor: str = "IMX500",
        sensorId: str = "100A505",
        kg: str = "1",
        application_processor: str = "3",
        led_on: bool = True,
    ):
        self.sensor = sensor
        self.sensorId = sensorId
        self.kg = kg
        self.application_processor = application_processor
        self.led_on = led_on

    def sample(self) -> Hardware:
        return Hardware(
            Sensor=self.sensor,
            SensorId=self.sensorId,
            KG=self.kg,
            ApplicationProcessor=self.application_processor,
            LedOn=self.led_on,
        )


class DnnModelVersionSampler:
    def __init__(self, root: list[str] = ["0308000000000100"]):
        self.root = root

    def sample(self) -> DnnModelVersion:
        return DnnModelVersion(root=self.root)


class VersionSampler:
    def __init__(
        self,
        sensor_fw_version: str = "010707",
        sensor_loader_version: str = "020301",
        dnn_model_version: DnnModelVersionSampler = DnnModelVersionSampler(),
        app_fw_version: str = "X700F6",
        app_loader_version: str = "D10200",
    ) -> None:
        self.ApFwVersion = app_fw_version
        self.ApLoaderVersion = app_loader_version
        self.DnnModelVersion = dnn_model_version
        self.SensorFwVersion = sensor_fw_version
        self.SensorLoaderVersion = sensor_loader_version

    def sample(self) -> Version:
        return Version(
            SensorFwVersion=self.SensorFwVersion,
            SensorLoaderVersion=self.SensorLoaderVersion,
            DnnModelVersion=self.DnnModelVersion.sample(),
            ApFwVersion=self.ApFwVersion,
            ApLoaderVersion=self.ApLoaderVersion,
        )


class StatusSampler:
    def __init__(
        self, sensor: str = "Standby", application_processor: str = "Idle"
    ) -> None:
        self.Sensor = sensor
        self.ApplicationProcessor = application_processor

    def sample(self) -> Status:
        return Status(
            Sensor=self.Sensor, ApplicationProcessor=self.ApplicationProcessor
        )


class OTASampler:
    def __init__(
        self,
        sensor_fw_last_update_date: str = "",
        sensor_loader_last_update_date: str = "",
        dnn_model_last_update_date: list[str] = [""],
        ap_fw_last_update_date: str = "",
        update_progress: float = 1,
        update_status: str = "Done",
    ) -> None:
        self.SensorFwLastUpdatedDate = sensor_fw_last_update_date
        self.SensorLoaderLastUpdatedDate = sensor_loader_last_update_date
        self.DnnModelLastUpdatedDate = dnn_model_last_update_date
        self.ApFwLastUpdatedDate = ap_fw_last_update_date
        self.UpdateProgress = update_progress
        self.UpdateStatus = update_status

    def sample(self) -> OTA:
        return OTA(
            SensorFwLastUpdatedDate=self.SensorFwLastUpdatedDate,
            SensorLoaderLastUpdatedDate=self.SensorLoaderLastUpdatedDate,
            DnnModelLastUpdatedDate=self.DnnModelLastUpdatedDate,
            ApFwLastUpdatedDate=self.ApFwLastUpdatedDate,
            UpdateProgress=self.UpdateProgress,
            UpdateStatus=self.UpdateStatus,
        )


class PermissionSampler:
    def __init__(self, factory_reset: bool = True) -> None:
        self.FactoryReset = factory_reset

    def sample(self) -> Permission:
        return Permission(FactoryReset=self.FactoryReset)


class DeviceConfigurationSampler:
    def __init__(
        self,
        hardware: HardwareSampler = HardwareSampler(),
        version: VersionSampler = VersionSampler(),
        status: StatusSampler = StatusSampler(),
        ota: OTASampler = OTASampler(),
        permission: PermissionSampler = PermissionSampler(),
        network: NetworkSampler = NetworkSampler(),
    ):
        self.hardware = hardware
        self.version = version
        self.status = status
        self.ota = ota
        self.permission = permission
        self.network = network

    def sample(self) -> DeviceConfiguration:
        return DeviceConfiguration(
            Hardware=self.hardware.sample(),
            Version=self.version.sample(),
            Status=self.status.sample(),
            OTA=self.ota.sample(),
            Permission=self.permission.sample(),
            Network=self.network.sample(),
        )
