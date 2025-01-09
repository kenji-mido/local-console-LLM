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
from unittest.mock import MagicMock

import trio
from local_console.core.device_services import DeviceServices


def mocked_device_services() -> DeviceServices:
    nursery = MagicMock(spec=trio.Nursery)
    channel = MagicMock(spec=trio.MemorySendChannel)
    token = MagicMock(spec=trio.lowlevel.TrioToken)
    return DeviceServices(nursery, channel, token)
