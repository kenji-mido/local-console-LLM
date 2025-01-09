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
from contextlib import contextmanager

from local_console.core.device_services import DeviceServices
from local_console.core.schemas.schemas import DeviceConnection


@contextmanager
def stored_devices(
    devices: list[DeviceConnection], device_services: DeviceServices | None = None
) -> Generator[None, None, None]:
    from local_console.core.config import config_obj

    config_obj.config.devices = devices
    if device_services:
        device_services.init_devices(devices)
    yield
