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
import logging

from mocked_device import command
from mocked_device.device import MockDevice
from mocked_device.mock_v1.device_v1 import MockDeviceV1
from mocked_device.mock_v1.filters.firmware import FirmwareFilterV1
from mocked_device.mock_v1.state_machines.firmware_machine import FirmwareMachineV1
from mocked_device.mock_v2.device_v2 import MockDeviceV2
from mocked_device.mock_v2.filters.firmware import FirmwareFilterV2
from mocked_device.mock_v2.state_machines.firmware_machine import FirmwareMachineV2
from mocked_device.mqtt.event import TopicListener
from mocked_device.mqtt.values import TargetedMqttMessage

logger = logging.getLogger(__name__)


class FirmwareListener(TopicListener):
    def __init__(self, device: MockDevice):
        self._state_machine: FirmwareMachineV1 | FirmwareMachineV2
        if isinstance(device, MockDeviceV1):
            self._state_machine = FirmwareMachineV1(device)
            self.filter = FirmwareFilterV1()
        if isinstance(device, MockDeviceV2):
            self._state_machine = FirmwareMachineV2(device)
            self.filter = FirmwareFilterV2()

    def handle(self, message: TargetedMqttMessage) -> None:
        content = self.filter.filter(message)
        if not content:
            return

        if not isinstance(content, command.Package):
            logger.error("Invalid package URI in firmware deployment")

        logger.debug(f"Adding uri to process {content.url}")
        self._state_machine.new_event(content.url)
