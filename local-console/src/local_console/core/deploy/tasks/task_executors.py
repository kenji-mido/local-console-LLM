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
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import trio
from local_console.core.deploy.tasks.base_task import Status
from local_console.core.deploy.tasks.base_task import Task
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes
from trio import Nursery
from trio import TASK_STATUS_IGNORED
from trio import TooSlowError
from typing_extensions import Self

logger = logging.getLogger(__name__)


class TaskEntity:
    def __init__(self, id: str, task: Task) -> None:
        self.id = id
        self.task = task

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TaskEntity):
            return self.id == other.id
        return False


class TaskExecutor(ABC):
    @abstractmethod
    async def add_task(self, task: Task) -> TaskEntity: ...
    @abstractmethod
    def list(self) -> list[TaskEntity]: ...


class TrioBackgroundTasks(TaskExecutor):
    def __init__(self) -> None:
        self._pending_tasks: list[Task] = []
        self._task_history: list[TaskEntity] = []
        self._running_tasks: dict[str, TaskEntity] = {}
        self._task_available = trio.Condition()
        self._stop_event = trio.Event()
        self._running_on: Nursery | None = None
        self._is_running: bool = False

    async def _errored(self, task: Task, error: BaseException) -> None:
        if task.get_state() == Status.RUNNING:
            await task.stop()
        task.errored(error)

    async def _raise_if_running(self, entity: TaskEntity) -> None:
        if entity.id in self._running_tasks:
            running = self._running_tasks[entity.id]
            if not running.task.get_state().status.is_finished():
                error = UserException(
                    code=ErrorCodes.EXTERNAL_DEPLOYMENT_ALREADY_RUNNING,
                    message="Another task is already running on the device",
                )
                await self._errored(entity.task, error)
                raise error

    async def add_task(self, task: Task) -> TaskEntity:
        async with self._task_available:
            id = task.id()
            entity = TaskEntity(id, task)
            await self._raise_if_running(entity)
            self._task_history.append(entity)
            logger.debug(f"Adding task {task.id()}")
            self._pending_tasks.append(task)
            self._task_available.notify()
            self._running_tasks[id] = entity
            return entity

    def list(self) -> list[TaskEntity]:
        return self._task_history

    async def _sandbox_run(self, task: Task) -> None:
        try:
            with trio.fail_after(task.timeout().timeout_in_seconds):
                await task.run()
                logger.debug(
                    f"Task {task.id()} finished with status {task.get_state()}"
                )
        except BaseException as e:
            logger.warning("Task has failed.", exc_info=e)
            if isinstance(e, TooSlowError):
                await self._errored(task, Exception("Timed out"))
            else:
                await self._errored(task, e)

    async def _infinite_pull_tasks(self) -> None:
        assert self._running_on
        while not self._stop_event.is_set():
            async with self._task_available:
                while not self._pending_tasks and not self._stop_event.is_set():
                    await self._task_available.wait()

                if self._pending_tasks:
                    task = self._pending_tasks.pop(0)
                    self._running_on.start_soon(self._sandbox_run, task)

    async def _run_tasks(
        self, nursery: Nursery, *, task_status: Any = TASK_STATUS_IGNORED
    ) -> None:
        self._is_running = True
        self._running_on = nursery
        task_status.started()
        await self._infinite_pull_tasks()
        self._is_running = False
        await self.stop()

    async def stop(self) -> None:
        for task in self.list():
            await task.task.stop()
        self._stop_event.set()
        async with self._task_available:
            self._task_available.notify()
        # TODO: Investigate pytest hang issue
        # Temporarily commented out to prevent pytest from hanging.

        # await EVENT_WAITING.wait_for(lambda: not self._is_running)

        if self._running_on:
            self._running_on.cancel_scope.cancel()
        self._running_on = None

    @asynccontextmanager
    async def run_forever(self) -> AsyncGenerator[Self, None]:
        async with trio.open_nursery() as nursery:
            await nursery.start(self._run_tasks, nursery)
            yield self  # Provide the task manager to the user
