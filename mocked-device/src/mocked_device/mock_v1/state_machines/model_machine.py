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

from mocked_device import command
from mocked_device.mock_v1.device_v1 import MockDeviceV1
from mocked_device.mock_v1.message import OTAUpdateStatus
from mocked_device.utils.request import download

logger = logging.getLogger(__name__)

MODEL_FAILURE_MARKER = "model_fail"


class ModelMachineV1:
    def __init__(self, device: MockDeviceV1) -> None:
        self._device = device
        self._pending_events: list[command.Delete | command.Package] = []
        self._thread: threading.Thread = threading.Thread(target=self.start)
        self._thread.start()

    def new_event(self, cmd: command.Delete | command.Package) -> None:
        self._pending_events.append(cmd)

    def _send_failure(self) -> None:
        logger.info("Simulate model deployment failure")
        self._device.status.OTA.UpdateStatus = OTAUpdateStatus.DOWNLOADING
        self._device.send_status()
        self._device.status.OTA.UpdateStatus = OTAUpdateStatus.UPDATING
        self._device.send_status()
        self._device.status.OTA.UpdateStatus = OTAUpdateStatus.FAILED
        self._device.send_status()

    def _send_status(self, cmd: command.Package) -> None:
        logger.info("Simulate model deployment")
        self._device.status.OTA.UpdateStatus = OTAUpdateStatus.DOWNLOADING
        self._device.send_status()
        self._device.status.OTA.UpdateStatus = OTAUpdateStatus.UPDATING
        self._device.send_status()
        self._device.status.Version.DnnModelVersion.append(cmd.version)
        self._device.status.OTA.UpdateStatus = OTAUpdateStatus.DONE
        self._device.send_status()

    def _send_delete(self, cmd: command.Delete) -> None:
        logger.info("Simulate model delete")
        self._device.status.OTA.UpdateStatus = OTAUpdateStatus.UPDATING
        self._device.send_status()
        if len(self._device.status.Version.DnnModelVersion) != 0:
            for full_network_id in self._device.status.Version.DnnModelVersion:
                if full_network_id[6:-4] == cmd.network_id:
                    self._device.status.Version.DnnModelVersion.remove(full_network_id)
        else:
            logger.debug("Model to delete not found")
        self._device.status.OTA.UpdateStatus = OTAUpdateStatus.DONE
        self._device.send_status()

    def _process_event(self, cmd: command.Delete | command.Package) -> None:
        if isinstance(cmd, command.Package):
            if MODEL_FAILURE_MARKER in cmd.url:
                self._send_failure()
            else:
                download(cmd.url)
                self._send_status(cmd)
        else:
            self._send_delete(cmd)

    def start(self) -> None:
        while True:
            while len(self._pending_events) > 0:
                next_event = self._pending_events.pop(0)
                logger.debug("Processing new model event")
                self._process_event(next_event)
            time.sleep(0.1)
