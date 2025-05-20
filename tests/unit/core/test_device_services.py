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
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from local_console.core.camera.enums import UnitScale
from local_console.core.camera.machine import Camera
from local_console.core.camera.states.v1.common import ConnectedCameraStateV1
from local_console.core.camera.streaming import image_dir_for
from local_console.core.camera.streaming import inference_dir_for
from local_console.core.config import Config
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes
from local_console.core.schemas.schemas import DeviceConnection
from local_console.core.schemas.schemas import DeviceID
from local_console.core.schemas.schemas import DeviceListItem
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.core.schemas.utils import get_default_device_dir_path

from tests.mocks.devices import mocked_device_services
from tests.strategies.samplers.configs import DeviceListItemSampler
from tests.strategies.samplers.device_config import DeviceConfigurationSampler
from tests.strategies.samplers.qr import QRInfoSampler


@pytest.mark.trio
async def test_adding_device_store_state() -> None:
    service = mocked_device_services()
    device = DeviceListItemSampler().sample()
    await service.add_device(device.name, device.id)

    assert device.id in service
    assert type(service.get_camera(device.id)) is Camera


@pytest.mark.trio
async def test_device_renaming(single_device_config) -> None:
    this_config = Config()
    service = mocked_device_services()

    start_name = "Nasarawa"
    device = DeviceListItemSampler(name=start_name).sample()
    await service.add_device(device.name, device.id)
    assert this_config.get_device_configs()[1].name == start_name

    new_name = "Kimbombo"
    service.rename_device(device.id, new_name)
    assert this_config.get_device_configs()[1].name == new_name
    assert len(this_config.get_device_configs()) == 2


def test_device_renaming_fails_on_validation_error(single_device_config) -> None:
    device = single_device_config.devices[0]
    service = mocked_device_services()

    str_256chars_long = "thisIsATrulyLong" * 16
    with pytest.raises(UserException) as error:
        service.rename_device(device.id, str_256chars_long)

    assert error.value.code == ErrorCodes.EXTERNAL_DEVICE_NAMES_TOO_LONG


@pytest.mark.trio
async def test_do_not_remove_last_device(single_device_config):
    device = single_device_config.devices[0]
    device_services = mocked_device_services()
    await device_services.add_device_to_internals(device)

    with pytest.raises(UserException) as e:
        device_services.remove_device(device.id)

    assert str(e.value) == "You need at least one device to work with"
    assert e.value.code == ErrorCodes.EXTERNAL_ONE_DEVICE_NEEDED


@pytest.mark.trio
async def test_device_remove(single_device_config) -> None:
    this_config = Config()
    service = mocked_device_services()

    device_1 = DeviceListItemSampler(name="device_1", port=2001).sample()
    await service.add_device(device_1.name, device_1.id)
    assert device_1.id in service
    assert device_1.id in {conn.id for conn in this_config.data.devices}

    device_2 = DeviceListItemSampler(name="device_2", port=2002).sample()
    await service.add_device(device_2.name, device_2.id)
    assert device_2.id in service
    assert device_2.id in {conn.id for conn in this_config.data.devices}

    with patch("local_console.core.device_services.Camera.shutdown") as mock_shutdown:
        service.remove_device(device_2.id)
        assert device_2.id not in service
        assert device_2.id not in {conn.id for conn in this_config.data.devices}

        mock_shutdown.assert_called_once()
        assert this_config._persistency_obj.write_count == 3


@pytest.mark.trio
async def test_remove_non_existent_device(single_device_config) -> None:
    this_config = Config()
    service = mocked_device_services()

    device_1 = DeviceListItemSampler(name="device_1").sample()
    await service.add_device(device_1.name, device_1.id)
    assert device_1.id in service
    assert device_1.id in {conn.id for conn in this_config.data.devices}

    previous_states = copy(service.get_cameras())
    previous_config_devices = {conn.id for conn in this_config.data.devices}

    with patch(
        "local_console.core.device_services.Camera.shutdown"
    ) as mock_shutdown, patch(
        "local_console.core.device_services.config_obj.save_config"
    ) as mock_save_config:
        service.remove_device(DeviceID("non-existent"))
        assert previous_states == service.get_cameras()
        assert previous_config_devices == {conn.id for conn in this_config.data.devices}

        mock_shutdown.assert_not_called()
        mock_save_config.assert_not_called()


@pytest.mark.trio
async def test_device_names_must_be_unique_when_adding(single_device_config) -> None:
    device = single_device_config.devices[0]
    service = mocked_device_services()

    attempted_new = DeviceListItem(
        name=device.name, id=DeviceID(1), port=1, onwire_schema=OnWireProtocol.EVP1
    )
    with pytest.raises(UserException) as e:
        await service.add_device(attempted_new.name, attempted_new.id)

    assert str(e.value).startswith("Device name")
    assert str(e.value).endswith("is already taken")
    assert e.value.code == ErrorCodes.EXTERNAL_DEVICE_NAMES_MUST_BE_UNIQUE


@pytest.mark.trio
async def test_load_device_from_config(tmp_path: Path, single_device_config) -> None:
    device = single_device_config.devices[0]

    _id = device.id
    Config().update_persistent_attr(_id, "device_dir_path", tmp_path)
    Config().update_persistent_attr(_id, "size", 31415)
    Config().update_persistent_attr(_id, "unit", UnitScale.KB)

    service = mocked_device_services()
    await service.init_devices([device])
    storage_watcher = service.get_camera(_id)._common_properties.dirs_watcher

    assert storage_watcher.current_limit == 31415 * 2**10
    assert set(storage_watcher._paths) == {
        image_dir_for(_id),
        inference_dir_for(_id),
    }


@pytest.mark.trio
async def test_network_info_from_device_info(single_device_config) -> None:
    device = single_device_config.devices[0]
    service = mocked_device_services()
    await service.init_devices(single_device_config.devices)

    camera = service.get_camera(device.id)
    camera._state = ConnectedCameraStateV1(camera._common_properties)

    status = DeviceConfigurationSampler().sample()
    camera._state._refresh_from_report(status)

    info = service.get_device(device.id)
    expected = status.Network
    network = info.modules[0].property.configuration.network_settings

    assert network.ip_address == expected.IPAddress
    assert network.gateway_address == expected.Gateway
    assert network.subnet_mask == expected.SubnetMask
    assert network.ntp_url == expected.NTP
    assert network.dns_address == expected.DNS


@pytest.mark.trio
async def test_network_info_from_qr(single_device_config) -> None:
    device = single_device_config.devices[0]
    qr_info = QRInfoSampler().sample()
    device.qr = qr_info
    service = mocked_device_services()
    await service.init_devices(single_device_config.devices)
    info = service.get_device(device.id)
    network = info.modules[0].property.configuration.network_settings

    assert network.ip_address == qr_info.ip_address
    assert network.gateway_address == qr_info.gateway
    assert network.subnet_mask == qr_info.subnet_mask
    assert network.ntp_url == qr_info.ntp
    assert network.dns_address == qr_info.dns


@pytest.mark.trio
async def test_endpoint_url_is_consolidated_qr_mqtt_host(single_device_config) -> None:
    device = single_device_config.devices[0]
    qr_info = QRInfoSampler().sample()
    device.qr = qr_info
    device.mqtt.host = "192.168.1.100"
    device.qr.mqtt_host = "192.168.1.200"

    service = mocked_device_services()
    await service.init_devices(single_device_config.devices)
    info = service.get_device(device.id)

    endpoints = info.modules[0].property.state.PRIVATE_endpoint_settings
    # Device information in GET /devices/{device_id} uses consolidated QR
    assert endpoints.endpoint_url == "192.168.1.200"
    # MQTT host remainins the same
    assert Config().get_device_config(device.id).mqtt.host == "192.168.1.100"


@pytest.mark.trio
async def test_endpoint_url_no_consolidated_qr_mqtt_host(single_device_config) -> None:
    device = single_device_config.devices[0]
    device.mqtt.host = "192.168.1.100"

    service = mocked_device_services()
    await service.init_devices(single_device_config.devices)
    info = service.get_device(device.id)

    endpoints = info.modules[0].property.state.PRIVATE_endpoint_settings
    # Device information in GET /devices/{device_id} uses mqtt.host instead of QR info
    assert endpoints.endpoint_url == "192.168.1.100"
    # MQTT host remains the same
    assert Config().get_device_config(device.id).mqtt.host == "192.168.1.100"


@pytest.mark.trio
@pytest.mark.parametrize("auto_delete_enabled", [False, True])
async def test_no_files_pruning_at_startup(
    auto_delete_enabled: bool, single_device_config
) -> None:
    dev_id = single_device_config.devices[0].mqtt.port
    Config().update_persistent_attr(dev_id, "auto_deletion", auto_delete_enabled)

    with patch("local_console.core.device_services.Camera") as mock_cs:
        mock_watcher = Mock()
        mock_cs.return_value.total_dir_watcher = mock_watcher
        service = mocked_device_services()
        await service.init_devices(single_device_config.devices)

        mock_watcher._prune.assert_not_called()


@pytest.mark.trio
async def test_reset_device_dir_path_if_error(single_device_config, tmp_path):
    device: DeviceConnection = single_device_config.devices[0]
    device_services = mocked_device_services()

    device.persist.auto_deletion = True
    device.persist.device_dir_path = "/"
    await device_services.add_device_to_internals(device)

    assert get_default_device_dir_path() == Config().get_persistent_attr(
        device.id, "device_dir_path"
    )
    assert not Config().get_persistent_attr(device.id, "auto_deletion")


@pytest.mark.trio
async def test_reset_device_dir_path(single_device_config, tmp_path):
    device: DeviceConnection = single_device_config.devices[0]
    device_services = mocked_device_services()

    device.persist.auto_deletion = True
    device.persist.device_dir_path = tmp_path
    await device_services.add_device_to_internals(device)

    assert get_default_device_dir_path() != Config().get_persistent_attr(
        device.id, "device_dir_path"
    )
    assert tmp_path == Config().get_persistent_attr(device.id, "device_dir_path")
    assert Config().get_persistent_attr(device.id, "auto_deletion")
