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
import threading
import time

from mocked_device.device import MockDevice
from mocked_device.mock.base import DeviceBehavior
from mocked_device.mock.handshake.listener import HandshakeListener
from mocked_device.mock.topics import MqttTopics
from mocked_device.mqtt.values import MqttMessage
from mocked_device.utils.random import random_id
from mocked_device.utils.timeout import EVENT_WAITING_2S

logger = logging.getLogger(__name__)

from mocked_device.mock.deployment.message import DeploymentStatusBuilder


class HandshakeBehavior(DeviceBehavior):
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None

    def _do_handshake(self, device: MockDevice) -> None:
        message_id = random_id()
        await_for_response = HandshakeListener(message_id)
        device.add_listener(await_for_response)
        handshake_message = MqttMessage(
            topic=MqttTopics.ATTRIBUTES_REQ.suffixed(message_id), payload=b"{}"
        )
        device.send_mqtt(handshake_message)
        EVENT_WAITING_2S.wait_for(lambda: await_for_response.finished)
        if not await_for_response.finished:
            logger.warning(
                f"Handshake timeout after {EVENT_WAITING_2S.timeout_in_seconds} seconds"
            )
        device.send_mqtt(
            DeploymentStatusBuilder(dnn_model_version=["0308000000000100"]).build()
        )

    def _keep_handshaking(self, device: MockDevice) -> None:
        while True:
            self._do_handshake(device)
            time.sleep(60)

    def apply_behavior(self, device: MockDevice) -> None:
        self._thread = threading.Thread(
            target=self._keep_handshaking, args=(device,), daemon=True
        )
        self._thread.start()


def handshake_behavior() -> HandshakeBehavior:
    return HandshakeBehavior()
