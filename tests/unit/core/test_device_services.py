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
from copy import copy
from pathlib import Path
from unittest.mock import patch

import pytest
from local_console.core.camera.state import CameraState
from local_console.core.device_services import get_model_info_from_dnn_model
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes
from local_console.core.schemas.schemas import DeviceListItem

from tests.mocks.devices import mocked_device_services
from tests.mocks.mock_configs import config_without_io
from tests.mocks.mock_configs import ConfigMocker
from tests.strategies.samplers.configs import DeviceConnectionSampler
from tests.strategies.samplers.configs import DeviceListItemSampler
from tests.strategies.samplers.configs import GlobalConfigurationSampler
from tests.strategies.samplers.device_config import DeviceConfigurationSampler
from tests.strategies.samplers.qr import QRInfoSampler


def test_adding_device_store_state() -> None:
    service = mocked_device_services()
    device = DeviceListItemSampler().sample()
    service.add_device(device.name, device.port)

    assert device.port in service.states
    assert type(service.states[device.port]) is CameraState


def test_device_renaming() -> None:

    simple_conf = GlobalConfigurationSampler(num_of_devices=1).sample()
    simple_conf.evp.iot_platform = "EVP1"
    with config_without_io(simple_conf) as this_config:
        service = mocked_device_services()

        start_name = "Nasarawa"
        device = DeviceListItemSampler(name=start_name).sample()
        service.add_device(device.name, device.port)
        assert this_config.get_device_configs()[1].name == start_name

        new_name = "Kimbombo"
        service.rename_device(device.port, new_name)
        assert this_config.get_device_configs()[1].name == new_name
        assert len(this_config.get_device_configs()) == 2


def test_device_renaming_fails_on_validation_error() -> None:
    simple_conf = GlobalConfigurationSampler(num_of_devices=1).sample()
    simple_conf.evp.iot_platform = "EVP1"
    device = simple_conf.devices[0]
    with config_without_io(simple_conf):
        service = mocked_device_services()

        str_256chars_long = "thisIsATrulyLong" * 16
        with pytest.raises(UserException) as error:
            service.rename_device(device.mqtt.port, str_256chars_long)

        assert error.value.code == ErrorCodes.EXTERNAL_DEVICE_NAMES_TOO_LONG


def test_do_not_remove_last_device():
    config_sample = GlobalConfigurationSampler(num_of_devices=1).sample()
    device_services = mocked_device_services()
    with ConfigMocker.mock_configuration(config_sample, device_services):
        device = config_sample.devices[0]
        with pytest.raises(UserException) as e:
            device_services.remove_device(device.mqtt.port)

        assert str(e.value) == "You need at least one device to work with"
        assert e.value.code == ErrorCodes.EXTERNAL_ONE_DEVICE_NEEDED


def test_device_remove() -> None:

    simple_conf = GlobalConfigurationSampler(num_of_devices=1).sample()
    simple_conf.evp.iot_platform = "EVP1"
    with config_without_io(simple_conf) as this_config:
        service = mocked_device_services()

        port_1 = 1234
        port_2 = 5678

        device_1 = DeviceListItemSampler(name="device_1", port=port_1).sample()
        service.add_device(device_1.name, device_1.port)
        assert device_1.port in service.states
        assert device_1.port in {conn.mqtt.port for conn in this_config._config.devices}

        device_2 = DeviceListItemSampler(name="device_2", port=port_2).sample()
        service.add_device(device_2.name, device_2.port)
        assert device_2.port in service.states
        assert device_2.port in {conn.mqtt.port for conn in this_config._config.devices}

        with patch(
            "local_console.core.device_services.CameraState.shutdown"
        ) as mock_shutdown, patch(
            "local_console.core.device_services.config_obj.save_config"
        ) as mock_save_config:
            service.remove_device(device_2.port)
            assert device_2.port not in service.states
            assert device_2.port not in {
                conn.mqtt.port for conn in this_config._config.devices
            }

            mock_shutdown.assert_called_once()
            mock_save_config.assert_called_once()


def test_remove_non_existent_device() -> None:

    simple_conf = GlobalConfigurationSampler(num_of_devices=1).sample()
    simple_conf.evp.iot_platform = "EVP1"
    with config_without_io(simple_conf) as this_config:
        service = mocked_device_services()

        port_1 = 1234
        port_2 = 5678

        device_1 = DeviceListItemSampler(name="device_1", port=port_1).sample()
        service.add_device(device_1.name, device_1.port)
        assert device_1.port in service.states
        assert device_1.port in {conn.mqtt.port for conn in this_config._config.devices}

        previous_states = copy(service.states)
        previous_config_devices = {
            conn.mqtt.port for conn in this_config._config.devices
        }

        with patch(
            "local_console.core.device_services.CameraState.shutdown"
        ) as mock_shutdown, patch(
            "local_console.core.device_services.config_obj.save_config"
        ) as mock_save_config:
            service.remove_device(port_2)
            assert previous_states == service.states
            assert previous_config_devices == {
                conn.mqtt.port for conn in this_config._config.devices
            }

            mock_shutdown.assert_not_called()
            mock_save_config.assert_not_called()


def test_device_names_must_be_unique_when_adding():

    simple_conf = GlobalConfigurationSampler(num_of_devices=1).sample()
    simple_conf.evp.iot_platform = "EVP1"
    with config_without_io(simple_conf):
        service = mocked_device_services()
        device = simple_conf.devices[0]

        attempted_new = DeviceListItem(name=device.name, port=device.mqtt.port + 1)
        with pytest.raises(UserException) as e:
            service.add_device(attempted_new.name, attempted_new.port)

        assert str(e.value).startswith("Device name")
        assert str(e.value).endswith("is already taken")
        assert e.value.code == ErrorCodes.EXTERNAL_DEVICE_NAMES_MUST_BE_UNIQUE


def test_load_device_from_config():
    simple_conf = GlobalConfigurationSampler(num_of_devices=1).sample()
    device = simple_conf.devices[0]
    device_con = DeviceConnectionSampler().sample()
    device_con.mqtt.port = device.mqtt.port
    device.persist.image_dir_path = "image/dir/path"
    device.persist.inference_dir_path = "inference/dir/path"
    device.persist.size = "31415"
    device.persist.unit = "Kb"
    with config_without_io(simple_conf):
        service = mocked_device_services()
        service.init_devices([device_con])
        device_result = service.get_state(device.mqtt.port)

        assert device_result.size.value == 31415
        assert device_result.unit.value == "Kb"
        assert device_result.image_dir_path.value == Path("image/dir/path")
        assert device_result.inference_dir_path.value == Path("inference/dir/path")


def test_network_info_from_device_info() -> None:
    simple_conf = GlobalConfigurationSampler(num_of_devices=1).sample()
    device = simple_conf.devices[0]
    with config_without_io(simple_conf):
        service = mocked_device_services()
        service.init_devices(simple_conf.devices)
        status = DeviceConfigurationSampler().sample()
        service.states[device.mqtt.port].device_config.value = status

        info = service.get_device(device.mqtt.port)

        expected = status.Network
        network = info.modules[0].property.state.network_settings

        assert network.ip_address == expected.IPAddress
        assert network.gateway_address == expected.Gateway
        assert network.subnet_mask == expected.SubnetMask
        assert network.ntp_url == expected.NTP
        assert network.dns_address == expected.DNS


def test_network_info_from_qr() -> None:
    simple_conf = GlobalConfigurationSampler(num_of_devices=1).sample()
    device = simple_conf.devices[0]
    qr_info = QRInfoSampler().sample()
    device.qr = qr_info
    with config_without_io(simple_conf):
        service = mocked_device_services()
        service.init_devices(simple_conf.devices)
        info = service.get_device(device.mqtt.port)
        network = info.modules[0].property.state.network_settings

        assert network.ip_address == qr_info.ip_address
        assert network.gateway_address == qr_info.gateway
        assert network.subnet_mask == qr_info.subnet_mask
        assert network.ntp_url == qr_info.ntp
        assert network.dns_address == qr_info.dns


@pytest.mark.parametrize(
    "model_info,exp_id,exp_vers,exp_conv",
    [("0311031111110100", "111111", "0100", "031103")],
)
def test_get_model_info_from_dnn_model(model_info, exp_id, exp_vers, exp_conv):
    network_id, model_version, converter_version = get_model_info_from_dnn_model(
        model_info
    )
    assert network_id == exp_id
    assert model_version == exp_vers
    assert converter_version == exp_conv


def test_endpoint_url_is_consolidated_qr_mqtt_host() -> None:
    simple_conf = GlobalConfigurationSampler(num_of_devices=1).sample()
    device = simple_conf.devices[0]
    qr_info = QRInfoSampler().sample()
    device.qr = qr_info

    device.mqtt.host = "192.168.1.100"
    device.qr.mqtt_host = "192.168.1.200"
    with config_without_io(simple_conf) as conf:
        service = mocked_device_services()
        service.init_devices(simple_conf.devices)
        info = service.get_device(device.mqtt.port)

        endpoints = info.modules[0].property.state.PRIVATE_endpoint_settings
        # Device information in GET /devices/{device_id} uses consolidated QR
        assert endpoints.endpoint_url == "192.168.1.200"
        # MQTT host remainins the same
        assert conf.get_device_config(device.mqtt.port).mqtt.host == "192.168.1.100"


def test_endpoint_url_no_consolidated_qr_mqtt_host() -> None:
    simple_conf = GlobalConfigurationSampler(num_of_devices=1).sample()
    device = simple_conf.devices[0]

    device.mqtt.host = "192.168.1.100"
    with config_without_io(simple_conf) as conf:
        service = mocked_device_services()
        service.init_devices(simple_conf.devices)
        info = service.get_device(device.mqtt.port)

        endpoints = info.modules[0].property.state.PRIVATE_endpoint_settings
        # Device information in GET /devices/{device_id} uses mqtt.host instead of QR info
        assert endpoints.endpoint_url == "192.168.1.100"
        # MQTT host remainins the same
        assert conf.get_device_config(device.mqtt.port).mqtt.host == "192.168.1.100"
