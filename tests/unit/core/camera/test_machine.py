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
from unittest.mock import Mock

import pytest
from local_console.core.camera.machine import Camera
from local_console.core.camera.states.base import Uninitialized
from local_console.core.schemas.schemas import DeviceConnection


@pytest.mark.trio
async def test_camera_initialization(nursery, single_device_config) -> None:
    config: DeviceConnection = single_device_config.devices[0]
    camera = Camera(config, Mock(), Mock(), Mock(), Mock(), lambda *args: None)
    assert isinstance(camera._state, Uninitialized)
    assert camera.id == config.id
    assert camera.device_type == "Unknown"
