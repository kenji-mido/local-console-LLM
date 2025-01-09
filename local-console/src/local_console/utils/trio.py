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
from typing import Callable

import trio
from local_console.utils.enums import StrEnum
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TaskStatus(StrEnum):
    STARTING = "starting"
    SUCCESS = "success"
    ERROR = "error"


class TimeoutConfig(BaseModel):
    pollin_interval_in_seconds: float = 0.1
    timeout_in_seconds: float = 30

    def num_of_iterations(self) -> int:
        if self.pollin_interval_in_seconds >= self.timeout_in_seconds:
            logger.warn(
                f"Invalid waiting times [{self.pollin_interval_in_seconds},{self.timeout_in_seconds}]"
            )
            return 1
        if self.pollin_interval_in_seconds == 0:
            logger.warn(
                f"Invalid waiting times [{self.pollin_interval_in_seconds},{self.timeout_in_seconds}]"
            )
            return 100
        return abs(int(self.timeout_in_seconds / self.pollin_interval_in_seconds))

    async def wait_for(self, condition: Callable[[], bool]) -> None:
        for _ in range(self.num_of_iterations()):
            if condition():
                break
            await trio.sleep(self.pollin_interval_in_seconds)


EVENT_WAITING = TimeoutConfig(pollin_interval_in_seconds=0.05, timeout_in_seconds=0.5)
DEFAULT_TASK_TIMEOUT = TimeoutConfig(
    pollin_interval_in_seconds=600, timeout_in_seconds=600
)


async def lock_until_started(
    status: Callable[[], TaskStatus],
    message: str = "Timeout exceeded",
    config: TimeoutConfig = TimeoutConfig(),
) -> None:
    for _ in range(config.num_of_iterations()):
        st = status()
        if st == TaskStatus.SUCCESS:
            return
        if st == TaskStatus.ERROR:
            break
        await trio.sleep(config.pollin_interval_in_seconds)
    raise TimeoutError(message)
