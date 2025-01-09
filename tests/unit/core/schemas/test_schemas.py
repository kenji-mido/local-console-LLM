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
from local_console.core.schemas.schemas import GlobalConfiguration

from tests.strategies.samplers.configs import DeviceConnectionSampler
from tests.strategies.samplers.configs import EVPParamsSampler


def test_active_device_verification():
    evp = EVPParamsSampler().sample()
    device = DeviceConnectionSampler().sample()
    with pytest.raises(ValueError):
        GlobalConfiguration(
            evp=evp, devices=[device], active_device=device.mqtt.port + 1
        )

    config = GlobalConfiguration(
        evp=evp, devices=[device], active_device=device.mqtt.port
    )

    with pytest.raises(ValueError):
        config.active_device = device.mqtt.port + 1
