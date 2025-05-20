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

from mocked_device.mock_v1.device_v1 import MockDeviceV1
from mocked_device.mock_v1.fake import UploadingParams
from mocked_device.mock_v1.filters.rpc import RPCFilterV1
from mocked_device.mock_v1.state_machines.streaming_machine import StreamingMachineV1
from mocked_device.mqtt.event import TopicListener
from mocked_device.mqtt.values import TargetedMqttMessage

logger = logging.getLogger(__name__)


class StreamingV1Listener(TopicListener):

    def __init__(self, device: MockDeviceV1):
        self._device = device
        self._filter = RPCFilterV1()
        self._state_machine = StreamingMachineV1(device)

    def topic(self) -> str:
        return self._filter.topic()

    def handle(self, message: TargetedMqttMessage) -> None:
        command = self._filter.filter(message)
        if command and command.method == "StartUploadInferenceData":
            params = UploadingParams.model_validate(command.params)
            logger.debug(f"Get payload {params}")
            self._state_machine.start_with(params)
            self._device.send_accepted(command)

        if command and command.method == "StopUploadInferenceData":
            self._state_machine.stop()
            self._device.send_accepted(command)
