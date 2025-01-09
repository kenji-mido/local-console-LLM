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
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes

from tests.mocks.mock_configs import config_without_io
from tests.strategies.samplers.configs import GlobalConfigurationSampler


def test_remove_device_only_1():
    simple_conf = GlobalConfigurationSampler(num_of_devices=1).sample()
    with config_without_io(simple_conf) as config:
        with pytest.raises(UserException) as e:
            config.remove_device(simple_conf.active_device)
            assert e.value.code == ErrorCodes.EXTERNAL_ONE_DEVICE_NEEDED
            assert e.value.message == "You need at least one device to work with"


def test_remove_device_2_devices():
    simple_conf = GlobalConfigurationSampler(num_of_devices=2).sample()
    with config_without_io(simple_conf) as config:
        config.remove_device(simple_conf.active_device)
        with pytest.raises(UserException) as e:
            config.remove_device(simple_conf.active_device)
            assert e.value.code == ErrorCodes.EXTERNAL_ONE_DEVICE_NEEDED
            assert e.value.message == "You need at least one device to work with"
