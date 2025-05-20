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
from datetime import timedelta

from mocked_device.mock_v2.device_v2 import MockDeviceV2
from mocked_device.mock_v2.ea_config import EdgeAppCommonSettings
from mocked_device.mock_v2.ea_config import ProcessState
from mocked_device.mock_v2.fake import as_timestamp
from mocked_device.mock_v2.fake import now
from mocked_device.mock_v2.fake import upload_fake_image
from mocked_device.mock_v2.fake import upload_fake_inference

logger = logging.getLogger(__name__)


# How often frames/inferences are produced
GENERATION_PERIOD = timedelta(seconds=2)


class StreamingMachineV2:
    def __init__(self, device: MockDeviceV2) -> None:
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._device = device

    def _stream(self, params: EdgeAppCommonSettings) -> None:
        assert params.port_settings

        while not self._stop_event.is_set():
            start = now()
            timestamp = as_timestamp(start)

            # Sudden conditions that should stop streaming
            if self.should_stop:
                self._stop_event.set()
                return

            if (
                params.port_settings.input_tensor
                and params.port_settings.input_tensor.enabled
            ):
                upload_fake_image(params, timestamp)

            if params.port_settings.metadata and params.port_settings.metadata.enabled:
                is_app_deployed = bool(self._device.device_assets.application)
                is_model_deployed = bool(
                    self._device.status.system_ai_model_deployment.targets
                )
                upload_fake_inference(
                    params,
                    self._device.device_assets.application,
                    is_app_deployed,
                    is_model_deployed,
                    timestamp,
                )

            period_remainder = (start + GENERATION_PERIOD) - now()
            self._stop_event.wait(timeout=period_remainder.total_seconds())

    def start_with(self, params: EdgeAppCommonSettings) -> None:
        self.stop()
        logger.debug("Start state machine")
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._stream, args=(params,), name="v2-streaming"
        )
        self._thread.start()

    def stop(self) -> None:
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join()
        logger.debug("State machine is stopped")

    @property
    def is_active(self) -> bool:
        return (
            isinstance(self._thread, threading.Thread)
            and self._thread.is_alive()
            and not self._stop_event.is_set()
        )

    @property
    def should_stop(self) -> bool:

        ea_conf = self._device.status.single_app_status.spec
        cs = ea_conf.common_settings
        if cs and cs.process_state:
            if cs.process_state == ProcessState.STOPPED:
                return True

        return False
