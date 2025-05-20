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

from mocked_device.device import MockDevice
from mocked_device.mock_v2.device_v2 import MockDeviceV2
from mocked_device.mock_v2.filters.device_configuration import (
    DeviceConfigurationFilterV2,
)
from mocked_device.mqtt.event import TopicListener
from mocked_device.mqtt.values import TargetedMqttMessage

logger = logging.getLogger(__name__)


class DeviceConfigurationV2Listener(TopicListener):
    def __init__(self, device: MockDevice):
        assert isinstance(device, MockDeviceV2)
        self._device = device
        self.filter = DeviceConfigurationFilterV2()

    def handle(self, message: TargetedMqttMessage) -> None:
        content = self.filter.filter(message)
        if content:
            logger.debug("Reconfiguring device")
            self._device._update_device_configuration(content)
