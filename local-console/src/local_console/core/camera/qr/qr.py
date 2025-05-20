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
from typing import Optional

import qrcode
from local_console.core.camera.qr.schema import QRInfo
from local_console.core.camera.schemas import PropertiesReport
from local_console.core.config import Config

logger = logging.getLogger(__name__)


def get_qr_object(
    mqtt_host: str,
    mqtt_port: Optional[int],
    tls_enabled: bool,
    ntp_server: str,
    ip_address: str = "",
    subnet_mask: str = "",
    gateway: str = "",
    dns_server: str = "",
    wifi_ssid: str = "",
    wifi_password: str = "",
    border: int = 5,
) -> qrcode.main.QRCode:
    """
    This function generates the QR code object that encodes the connection
    settings for a camera device.

    :param mqtt_host:   Address of MQTT broker host
    :param mqtt_port:   TCP port on which the MQTT broker is listening
    :param tls_enabled: Is TLS enabled?
    :param ntp_server:  NTP server for the camera to get its time synced
    :param ip_address:  Static IP address of the camera device
    :param subnet_mask: Address of Subnet Mask
    :param gateway:     Address of Gateway
    :param dns_server:  Address of DNS server
    :param wifi_ssid:   Wireless LAN router SSID
    :param wifi_password: Wireless LAN router connection password
    :param border:      size of padding around the QR code
    :return: the QR object containing the code for the camera
    """

    # Minimum border is 4 according to the specs
    border = 4 if border < 4 else border

    # This verbosity is to blame between types-qrcode and mypy
    # It should be instead: qr_code = qrcode.QRCode(...
    qr_code: qrcode.main.QRCode = qrcode.main.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        border=border,
    )
    qr_code.add_data(
        qr_string(
            mqtt_host,
            mqtt_port,
            tls_enabled,
            ntp_server,
            ip_address,
            subnet_mask,
            gateway,
            dns_server,
            wifi_ssid,
            wifi_password,
        )
    )
    qr_code.make(fit=True)

    return qr_code


def qr_string(
    mqtt_host: str,
    mqtt_port: Optional[int],
    tls_enabled: bool,
    ntp_server: str,
    ip_address: str = "",
    subnet_mask: str = "",
    gateway: str = "",
    dns_server: str = "",
    wifi_ssid: str = "",
    wifi_password: str = "",
) -> str:
    # Followed the order of the Setup Enrollment on the Console.
    tls_flag = 0 if tls_enabled else 1
    output = f"AAIAAAAAAAAAAAAAAAAAAA==N=11;E={mqtt_host};H={mqtt_port};t={tls_flag}"
    if wifi_ssid:
        output += f";S={wifi_ssid}"
    if wifi_password:
        output += f";P={wifi_password}"
    if ip_address:
        output += f";I={ip_address}"
    if subnet_mask:
        output += f";K={subnet_mask}"
    if gateway:
        output += f";G={gateway}"
    if dns_server:
        output += f";D={dns_server}"
    output += f";T={ntp_server};U1FS"
    return output


class QRService:
    def __init__(self) -> None:
        self.in_memory: list[QRInfo] = []

    def generate(self, info: QRInfo) -> qrcode.main.QRCode:
        self.in_memory.append(info)
        return get_qr_object(
            mqtt_host=info.mqtt_host,
            mqtt_port=info.mqtt_port,
            tls_enabled=False,
            ntp_server=info.ntp,
            ip_address=info.ip_address,
            subnet_mask=info.subnet_mask,
            gateway=info.gateway,
            dns_server=info.dns,
            wifi_ssid=info.wifi_ssid,
            wifi_password=info.wifi_pass,
        )

    def _qr_match_device_state(
        self, port: int, qr: QRInfo, device_state: PropertiesReport
    ) -> bool:
        return (
            qr.mqtt_port == port
            and qr.ntp == device_state.ntp_url
            and qr.ip_address == device_state.ip_address
            and qr.subnet_mask == device_state.subnet_mask
            and qr.gateway == device_state.gateway_address
            and qr.dns == device_state.dns_address
        )

    def _update_device_with_qr(self, qr: QRInfo) -> None:
        for device in Config().data.devices:
            if device.mqtt.port == qr.mqtt_port:
                device.qr = qr
                device.mqtt.host = qr.mqtt_host
                Config().save_config()
                break

    def _save_best_qr_on_disk(self, port: int, device_state: PropertiesReport) -> None:
        for qr in reversed(self.in_memory):
            if self._qr_match_device_state(port, qr, device_state):
                self._update_device_with_qr(qr)
                logger.info(
                    f"Consolidated QR code from memory with wifi sid {qr.wifi_ssid}"
                )
                break

        if len(self.in_memory) > 0:
            logger.debug("Could not find any of the qr to consolidate with")

    def _forget_all_qr_on_port(self, port: int) -> None:
        before_cleaning = len(self.in_memory)
        self.in_memory = [qr for qr in self.in_memory if qr.mqtt_port != port]
        logger.info(
            f"After consolidation there have been {before_cleaning - len(self.in_memory)} removed qrs from memory"
        )

    def persist_to(
        self,
        port: int,
        device_state: PropertiesReport,
    ) -> None:
        self._save_best_qr_on_disk(port, device_state)
        self._forget_all_qr_on_port(port)
