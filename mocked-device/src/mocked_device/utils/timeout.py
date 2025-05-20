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

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TimeoutConfig(BaseModel):
    pollin_interval_in_seconds: float = 0.1
    timeout_in_seconds: float = 30

    def num_of_iterations(self) -> int:
        if self.pollin_interval_in_seconds >= self.timeout_in_seconds:
            logger.warning(
                f"Invalid waiting times [{self.pollin_interval_in_seconds},{self.timeout_in_seconds}]"
            )
            return 1
        if self.pollin_interval_in_seconds == 0:
            logger.warning(
                f"Invalid waiting times [{self.pollin_interval_in_seconds},{self.timeout_in_seconds}]"
            )
            return 100
        return abs(int(self.timeout_in_seconds / self.pollin_interval_in_seconds))

    def wait_for(self, condition: Callable[[], bool]) -> None:
        for _ in range(self.num_of_iterations()):
            if condition():
                break
            time.sleep(self.pollin_interval_in_seconds)


EVENT_WAITING_2S = TimeoutConfig(pollin_interval_in_seconds=0.1, timeout_in_seconds=2)
