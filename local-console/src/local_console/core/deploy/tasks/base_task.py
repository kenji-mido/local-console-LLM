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
from abc import ABC
from abc import abstractmethod
from datetime import datetime
from typing import Any

from local_console.utils.enums import StrEnum
from local_console.utils.trio import DEFAULT_TASK_TIMEOUT
from local_console.utils.trio import TimeoutConfig
from pydantic import BaseModel
from pydantic import Field
from typing_extensions import Self

logger = logging.getLogger(__name__)


class Status(StrEnum):
    INITIALIZING = "Initializing"
    RUNNING = "Deploying"
    SUCCESS = "Success"
    ERROR = "Fail"

    def is_finished(self) -> bool:
        return self in [Status.SUCCESS, Status.ERROR]


class TaskState(BaseModel):
    status: Status = Status.INITIALIZING
    started_at: datetime = Field(default_factory=datetime.now)
    error: str | None = None

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, TaskState):
            return super().__eq__(other)
        elif isinstance(other, Status):
            return self.status == other
        return False

    def __repr__(self) -> str:
        return f"TaskStatus(status={self.status},error={self.error})"

    def __str__(self) -> str:
        return self.__repr__()

    def set(self, new_status: Status) -> Self:
        if self.status.is_finished():
            logger.info(
                f"Update task status to:{new_status} while current status is {self.status}"
            )
        else:
            logger.debug(f"Change task status from {self.status} to {new_status}")
            self.status = new_status
        return self

    def get(self) -> Status:
        return self.status

    def error_notification(self, error_message: str) -> Self:
        logger.debug(f"Error notification received: {error_message}")
        self.set(Status.ERROR)
        if not self.error:
            self.error = error_message
        return self

    def handle_exception(self, exception: BaseException) -> Self:
        self.error_notification(str(exception))
        return self

    def that_started_at(self, started: datetime) -> Self:
        return self.model_copy(update={"started_at": started})


class DeployHistoryInfo(BaseModel): ...


class Task(ABC):
    @abstractmethod
    async def run(self) -> None: ...
    @abstractmethod
    def get_state(self) -> TaskState: ...
    @abstractmethod
    def errored(self, error: BaseException) -> None: ...
    @abstractmethod
    async def stop(self) -> None: ...
    @abstractmethod
    def id(self) -> str: ...
    def timeout(self) -> TimeoutConfig:
        return DEFAULT_TASK_TIMEOUT

    def get_deploy_history_info(self) -> DeployHistoryInfo:
        return DeployHistoryInfo()
