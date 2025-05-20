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
import pytest
from local_console.core.config import Config
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes
from local_console.core.schemas.schemas import DeviceConnection

from tests.mocks.config import set_configuration
from tests.strategies.samplers.configs import GlobalConfigurationSampler


def port(dev: DeviceConnection) -> int:
    return dev.mqtt.port


def test_remove_device_only_1(single_device_config):
    last_device = single_device_config.devices[0]
    with pytest.raises(UserException) as e:
        Config().remove_device(port(last_device))
        assert e.value.code == ErrorCodes.EXTERNAL_ONE_DEVICE_NEEDED
        assert e.value.message == "You need at least one device to work with"


def test_remove_device_2_devices():
    simple_conf = GlobalConfigurationSampler(num_of_devices=2).sample()
    set_configuration(simple_conf)
    device1 = simple_conf.devices[0]
    device2 = simple_conf.devices[1]

    Config().remove_device(port(device1))
    with pytest.raises(UserException) as e:
        Config().remove_device(port(device2))
        assert e.value.code == ErrorCodes.EXTERNAL_ONE_DEVICE_NEEDED
        assert e.value.message == "You need at least one device to work with"


def test_persistent_attribute_methods(tmp_path, single_device_config):
    config_obj = Config()
    persist = config_obj._persistency_obj
    device1 = single_device_config.devices[0]
    persistent_attr = "device_dir_path"

    assert len(config_obj.data.devices) == 1

    first_value = config_obj.get_persistent_attr(device1.mqtt.port, persistent_attr)
    assert persist.read_count == 0
    assert persist.write_count == 0

    config_obj.update_persistent_attr(device1.mqtt.port, persistent_attr, tmp_path)
    assert persist.read_count == 0
    assert persist.write_count == 1

    new_value = config_obj.get_persistent_attr(device1.mqtt.port, persistent_attr)
    assert persist.read_count == 0
    assert persist.write_count == 1

    config_obj.read_config()
    assert persist.read_count == 1
    assert persist.write_count == 1

    assert new_value != first_value
    assert new_value == tmp_path
