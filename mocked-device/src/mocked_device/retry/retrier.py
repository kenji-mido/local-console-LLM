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
import time
from typing import Callable
from typing import Generic
from typing import TypeVar

from mocked_device.utils.timeout import TimeoutConfig

logger = logging.getLogger(__name__)

RESULT = TypeVar("RESULT")


class Retry(Generic[RESULT]):
    def __init__(
        self,
        retry: Callable[[], RESULT],
        until: Callable[[RESULT], bool] = lambda x: x is not None,
        timeout: TimeoutConfig = TimeoutConfig(
            pollin_interval_in_seconds=1, timeout_in_seconds=600
        ),
    ):
        self._retry = retry
        self._until = until
        self._timeout = timeout

    def get(self) -> RESULT | None:
        last_exception: BaseException | None = None
        result: RESULT | None = None
        for _ in range(self._timeout.num_of_iterations()):
            try:
                last_exception = None
                result = self._retry()
                if self._until(result):
                    break
            except BaseException as e:
                logger.debug(f"Keep retrying as we did get an error {str(e)}")
                last_exception = e
            time.sleep(self._timeout.pollin_interval_in_seconds)
        if not result and last_exception:
            raise last_exception
        return result
