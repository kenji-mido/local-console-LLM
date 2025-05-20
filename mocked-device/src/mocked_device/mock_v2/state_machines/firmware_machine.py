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

from mocked_device.mock_v2.device_v2 import MockDeviceV2
from mocked_device.utils.request import download

logger = logging.getLogger(__name__)

FIRMWARE_FAILURE_MARKER = "firmware_fail"


class FirmwareMachineV2:
    def __init__(self, device: MockDeviceV2) -> None:
        self._device = device
        self._pending_events: list[str] = []
        self._thread: threading.Thread = threading.Thread(target=self.start)
        self._thread.start()

    def new_event(self, package_uri: str) -> None:
        self._pending_events.append(package_uri)

    def _send_status(self) -> None:
        logger.debug("Not yet implemented")

    def _send_failure(self) -> None:
        logger.debug("Not yet implemented")

    def _process_event(self, package_uri: str) -> None:
        logger.info(f"Processing firmware download {package_uri}")
        if FIRMWARE_FAILURE_MARKER in package_uri:
            self._send_failure()
        else:
            download(package_uri)
            self._send_status()
            logger.info("The fake deployment event has been processed")

    def start(self) -> None:
        while True:
            while len(self._pending_events) > 0:
                next_event = self._pending_events.pop(0)
                logger.debug(f"Processing new firmware event {next_event}")
                self._process_event(next_event)
            time.sleep(0.1)
