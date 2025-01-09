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
from local_console.core.camera.qr.schema import QRInfo


class QRInfoSampler:
    def __init__(
        self,
        mqtt_host: str = "192.168.1.1",
        mqtt_port: int = 1883,
        ntp: str = "pool.ntp.org",
        ip_address: str = "192.168.1.2",
        subnet_mask: str = "255.255.255.0",
        gateway: str = "192.168.1.3",
        dns: str = "8.8.8.8",
        wifi_ssid: str = "WIFI-SSSID",
        wifi_pass: str = "do-not-share",
    ):
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.ntp = ntp
        self.ip_address = ip_address
        self.subnet_mask = subnet_mask
        self.gateway = gateway
        self.dns = dns
        self.wifi_ssid = wifi_ssid
        self.wifi_pass = wifi_pass

    def sample(self) -> QRInfo:
        return QRInfo(
            mqtt_host=self.mqtt_host,
            mqtt_port=self.mqtt_port,
            ntp=self.ntp,
            ip_address=self.ip_address,
            subnet_mask=self.subnet_mask,
            gateway=self.gateway,
            dns=self.dns,
            wifi_ssid=self.wifi_ssid,
            wifi_pass=self.wifi_pass,
        )
