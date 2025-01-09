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
from mocked_device.mock.deployment.message import DeploymentStatusBuilder
from mocked_device.utils.request import download

logger = logging.getLogger(__name__)


class StateMachine:
    def __init__(self, device: MockDevice) -> None:
        self._event_iterator = 0
        self._device = device
        self._pending_events: list[str] = []
        self._thread: threading.Thread = threading.Thread(
            target=self.start, daemon=True
        )
        self._thread.start()

    def new_event(self, package_uri: str) -> None:
        self._pending_events.append(package_uri)

    def _send_status(self) -> None:
        logger.info("Simulate device status")
        dnn_model_version = ["0308000000000100"]
        msg = DeploymentStatusBuilder(
            dnn_model_version=dnn_model_version, ota_update_status="Downloading"
        ).build()
        self._device.send_mqtt(msg)
        msg = DeploymentStatusBuilder(
            dnn_model_version=dnn_model_version, ota_update_status="Updating"
        ).build()
        self._device.send_mqtt(msg)
        msg = DeploymentStatusBuilder(
            dnn_model_version=dnn_model_version, ota_update_status="Done"
        ).build()
        self._device.send_mqtt(msg)

    def _process_event(self, package_uri: str) -> None:
        logger.info(f"Processing firmware request event {self._event_iterator}")
        if self._event_iterator == 0:
            logger.info(f"Processing firmware download {package_uri}")
            download(package_uri)
        self._send_status()
        self._event_iterator = (self._event_iterator + 1) % 3
        logger.info("The fake deployment event has been processed")

    def start(self) -> None:
        while True:
            while len(self._pending_events) > 0:
                next_event = self._pending_events.pop()
                logger.debug("Processing new firmware event")
                self._process_event(next_event)
            time.sleep(0.1)
