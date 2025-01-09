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
from typing import Callable

from mocked_device.device import MockDevice
from mocked_device.mock.base import DeviceBehavior
from mocked_device.mock.deployment.firmware.listener import FirmwareListener


class FirmwareBehavior(DeviceBehavior):
    def __init__(
        self, listener_builder: Callable[[MockDevice], FirmwareListener]
    ) -> None:
        self._listener_builder = listener_builder

    def apply_behavior(self, device: MockDevice) -> None:
        device.add_listener(self._listener_builder(device))


def deploy_firmware_behavior() -> FirmwareBehavior:
    return FirmwareBehavior(lambda device: FirmwareListener(device))
