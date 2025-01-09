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

from mocked_device.mock.rpc.streaming.fake import now_str
from mocked_device.mock.rpc.streaming.fake import upload_fake_image
from mocked_device.mock.rpc.streaming.fake import upload_fake_inference
from mocked_device.mock.rpc.streaming.values import UploadingParams
from mocked_device.utils.timeout import TimeoutConfig

logger = logging.getLogger(__name__)


class StateMachine:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def _stream(self, params: UploadingParams) -> None:
        timeout = TimeoutConfig(
            pollin_interval_in_seconds=0.05, timeout_in_seconds=params.interval
        )
        while not self._stop_event.is_set():
            timestamp = now_str()
            upload_fake_image(params, timestamp)
            upload_fake_inference(params, timestamp)
            timeout.wait_for(lambda: self._stop_event.is_set())

    def start_with(self, params: UploadingParams) -> None:
        self.stop()
        logger.debug("Start state machine")
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._stream, args=(params,), daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join()
        logger.debug("State machine is stopped")
