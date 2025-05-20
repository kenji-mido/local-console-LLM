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
from collections.abc import Generator

import pytest
from local_console.core.schemas.schemas import GlobalConfiguration

from tests.mocks.config import set_configuration
from tests.strategies.samplers.configs import DeviceConnectionSampler
from tests.strategies.samplers.configs import GlobalConfigurationSampler


@pytest.fixture
def single_device_config() -> Generator[GlobalConfiguration, None, None]:
    """
    Sets a single-device sample configuration for a test.
    This is intended to work alongside conftest.py::reset_global_config.

    This fixture is also invoked by other fixtures under `tests.fixtures.*`
    In order for that to work, `single_device_config` must be imported from
    the test suite module that uses one of those fixtures, even if this
    fixture is not instantiated directly by that test module.
    """
    device_gen = DeviceConnectionSampler(name="dev")
    simple_conf = GlobalConfigurationSampler(
        num_of_devices=1, devices=device_gen
    ).sample()
    set_configuration(simple_conf)
    yield simple_conf
