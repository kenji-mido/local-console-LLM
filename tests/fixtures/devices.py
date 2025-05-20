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
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import trio
from local_console.core.device_services import DeviceServices
from local_console.core.schemas.schemas import DeviceConnection

from tests.fixtures.agent import mocked_agent
from tests.mocks.config import set_configuration
from tests.mocks.http import mocked_http_server
from tests.strategies.samplers.configs import GlobalConfigurationSampler


@asynccontextmanager
async def unmocked_device_service() -> AsyncGenerator[DeviceServices, None]:
    with mocked_http_server() as webserver:
        async with trio.open_nursery() as nursery:
            send, _ = trio.open_memory_channel(0)
            token = trio.lowlevel.current_trio_token()
            yield DeviceServices(nursery, send, webserver, token)


@asynccontextmanager
async def stored_devices(
    devices: list[DeviceConnection], device_services: DeviceServices | None = None
) -> AsyncGenerator[None, None]:

    global_config_sample = GlobalConfigurationSampler(num_of_devices=0).sample()
    global_config_sample.devices = devices
    set_configuration(global_config_sample)

    with mocked_agent() as agent:
        if device_services:
            await device_services.init_devices(devices)
        yield
        agent.stop_receiving_messages()
