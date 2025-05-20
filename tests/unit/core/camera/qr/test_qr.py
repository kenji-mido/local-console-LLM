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
from local_console.commands import qr
from local_console.core.camera.qr.qr import QRService
from local_console.core.camera.qr.schema import QRInfo
from local_console.core.camera.states.v1.common import populate_properties
from local_console.core.config import Config
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.core.schemas.schemas import GlobalConfiguration

from tests.mocks.config import set_configuration
from tests.strategies.samplers.configs import GlobalConfigurationSampler
from tests.strategies.samplers.device_config import DeviceConfigurationSampler
from tests.strategies.samplers.device_config import NetworkSampler
from tests.strategies.samplers.qr import QRInfoSampler


def test_qr_code_generation() -> None:

    service = QRService()
    info = QRInfoSampler().sample()

    qr = service.generate(info)
    values = f"==N=11;E={info.mqtt_host};H={info.mqtt_port};t=1;S={info.wifi_ssid};P={info.wifi_pass};I={info.ip_address};K={info.subnet_mask};G={info.gateway};D={info.dns};T={info.ntp};U1FS"
    assert qr.data_list[1].data == values.encode("utf-8")


def test_qr_code_translate_ips() -> None:

    service = QRService()
    info = QRInfoSampler(mqtt_host="localhost", ntp="localhost").sample()

    qr = service.generate(info)
    values = f"==N=11;E={info.mqtt_host};H={info.mqtt_port};t=1;S={info.wifi_ssid};P={info.wifi_pass};I={info.ip_address};K={info.subnet_mask};G={info.gateway};D={info.dns};T={info.ntp};U1FS"
    assert qr.data_list[1].data == values.encode("utf-8")


def qr_from(device_config: GlobalConfiguration) -> QRInfo:
    return QRInfoSampler(
        mqtt_host=device_config.Network.ProxyURL,
        mqtt_port=device_config.Network.ProxyPort,
        ip_address=device_config.Network.IPAddress,
        ntp=device_config.Network.NTP,
        dns=device_config.Network.DNS,
        subnet_mask=device_config.Network.SubnetMask,
        gateway=device_config.Network.Gateway,
    ).sample()


def test_consolidation(single_device_config) -> None:
    service = QRService()
    device = single_device_config.devices[0]
    device_config = DeviceConfigurationSampler().sample()
    assert not single_device_config.devices[0].qr

    qr_info = qr_from(device_config)
    device_config.Network.ProxyPort = 0
    device_config.Network.ProxyURL = ""

    service.generate(qr_info)
    service.persist_to(device.mqtt.port, populate_properties(device_config))

    assert Config().data.devices[0].qr == qr_info


def test_consolidation_choose_if_all_match(single_device_config) -> None:
    service = QRService()
    device = single_device_config.devices[0]
    device_config = DeviceConfigurationSampler().sample()
    assert not single_device_config.devices[0].qr

    qr_info = qr_from(device_config)
    device_config.Network.ProxyPort = 0
    device_config.Network.ProxyURL = ""
    qr_info.gateway = f"DifferentFrom{device_config.Network.Gateway}"

    service.generate(qr_info)
    service.persist_to(device.mqtt.port, populate_properties(device_config))

    assert not Config().data.devices[0].qr


def test_consolidate_choose_the_newest(single_device_config) -> None:
    service = QRService()
    device = single_device_config.devices[0]
    device_config = DeviceConfigurationSampler().sample()
    assert not single_device_config.devices[0].qr

    qr_info1 = qr_from(device_config)
    qr_info1.wifi_ssid = "WIFI1"
    qr_info2 = qr_from(device_config)
    qr_info2.wifi_ssid = "WIFI2"
    device_config.Network.ProxyPort = 0
    device_config.Network.ProxyURL = ""

    service.generate(qr_info1)
    service.generate(qr_info2)
    service.persist_to(device.mqtt.port, populate_properties(device_config))

    assert Config().data.devices[0].qr == qr_info2


def test_consolidate_clean_after_each_consolidation(single_device_config) -> None:
    service = QRService()
    device = single_device_config.devices[0]
    device_config = DeviceConfigurationSampler().sample()
    assert not single_device_config.devices[0].qr

    qr_info = qr_from(device_config)
    device_config.Network.ProxyPort = 0
    device_config.Network.ProxyURL = ""

    service.generate(qr_info)
    device_config.Network.IPAddress = "force-consolidation-to-fail"

    # This consolidation forgets all the elements that have the device port
    service.persist_to(device.mqtt.port, populate_properties(device_config))
    assert not Config().data.devices[0].qr

    # This consolidation should work but will not consolidate as the previous one remove all previous ones
    device_config.Network.IPAddress = qr_info.ip_address
    service.persist_to(device.mqtt.port, populate_properties(device_config))
    assert not Config().data.devices[0].qr


def test_work_with_multiple_devices() -> None:
    configuration = GlobalConfigurationSampler(num_of_devices=5).sample()
    set_configuration(configuration)

    service = QRService()
    for device in configuration.devices:

        device_config = DeviceConfigurationSampler().sample()
        device_config.Network.ProxyPort = device.mqtt.port
        stored_device = [
            dev for dev in Config().data.devices if dev.mqtt.port == device.mqtt.port
        ][0]
        assert not stored_device.qr

        qr_info1 = qr_from(device_config)
        qr_info1.wifi_ssid = "WIFI1"
        qr_info2 = qr_from(device_config)
        qr_info2.wifi_ssid = "WIFI2"
        device_config.Network.ProxyPort = 0
        device_config.Network.ProxyURL = ""

        service.generate(qr_info1)
        service.generate(qr_info2)

        service.persist_to(device.mqtt.port, populate_properties(device_config))

        assert stored_device.qr == qr_info2


def empty_config() -> DeviceConfiguration:
    return DeviceConfigurationSampler(
        network=NetworkSampler(
            proxy_url="",
            proxy_port=0,
            proxy_username="",
            ip_address="",
            subnet_mask="",
            gateway="",
            dns="",
            ntp="pool.ntp.org",
        )
    ).sample()


def static_ip(port: int) -> QRInfo:
    return QRInfoSampler(
        mqtt_host="10.42.0.1",
        mqtt_port=port,
        ntp="pool.ntp.org",
        ip_address="10.42.0.2",
        subnet_mask="255.255.255.0",
        gateway="10.42.0.1",
        dns="8.8.8.8",
        wifi_ssid="static-wifi",
        wifi_pass="static pass",
    )


def dynamic_ip(port: int, ssid: str, password: str) -> QRInfo:
    return QRInfoSampler(
        mqtt_host="192.168.10.123",
        mqtt_port=port,
        ntp="pool.ntp.org",
        ip_address="",
        subnet_mask="",
        gateway="",
        dns="",
        wifi_ssid=ssid,
        wifi_pass=password,
    )


def test_consolidation_dynamic_ip(single_device_config) -> None:
    service = QRService()
    device = single_device_config.devices[0]
    port = device.mqtt.port
    device_config = DeviceConfigurationSampler().sample()
    assert not single_device_config.devices[0].qr

    device_config = empty_config()
    qr_static = static_ip(port).sample()
    qr_dyn_1 = dynamic_ip(port, "ssid-1", "pass-1").sample()
    qr_dyn_2 = dynamic_ip(port, "ssid-2", "pass-3").sample()

    device_config.Network.ProxyPort = 0
    device_config.Network.ProxyURL = ""

    service.generate(qr_dyn_1)
    service.generate(qr_static)
    service.generate(qr_dyn_2)

    service.persist_to(device.mqtt.port, populate_properties(device_config))

    assert Config().data.devices[0].qr == qr_dyn_2
