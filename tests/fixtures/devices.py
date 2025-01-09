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


@asynccontextmanager
async def with_real_device_service() -> AsyncGenerator[DeviceServices, None]:
    async with trio.open_nursery() as nursery:
        send, _ = trio.open_memory_channel(0)
        token = trio.lowlevel.current_trio_token()
        yield DeviceServices(nursery, send, token)
