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
from unittest.mock import MagicMock

import pytest
import trio
from local_console.core.camera.state import CameraState
from local_console.core.deploy.tasks.base_task import Status
from local_console.core.deploy.tasks.base_task import Task
from local_console.core.deploy.tasks.base_task import TaskState
from local_console.core.deploy.tasks.config_task import ConfigTask
from local_console.core.deploy.tasks.firmware_task import FirmwareTask
from local_console.core.deploy.tasks.task_executors import TrioBackgroundTasks
from local_console.core.error.base import UserException
from local_console.core.schemas.schemas import DeploymentConfig
from local_console.utils.trio import TimeoutConfig

from tests.mocks.tasks import mocked_app_tasks
from tests.mocks.tasks import mocked_config_tasks
from tests.mocks.tasks import mocked_firmware_tasks
from tests.mocks.tasks import mocked_model_tasks
from tests.mocks.tasks import mocked_task


def errored_with(mocked_task: Task, error_message: str = "Task failure") -> Task:
    mocked_error = Exception(error_message)
    mocked_task.run.side_effect = mocked_error
    return mocked_task


@pytest.mark.trio
async def test_isolate_task_failure():
    errored_task = mocked_task()
    healthy_task = mocked_task(
        timeout=TimeoutConfig(timeout_in_seconds=10, pollin_interval_in_seconds=0.005)
    )
    errored_with(errored_task, "Task failure")
    executor = TrioBackgroundTasks()
    async with executor.run_forever():

        await executor.add_task(healthy_task)
        await trio.sleep(0.005)
        await executor.add_task(errored_task)
        await trio.sleep(0.005)

        assert healthy_task.get_state() == Status.RUNNING
        assert errored_task.get_state() == Status.ERROR
        assert errored_task.get_state().error == "Task failure"
        healthy_task.stop()
        await executor.stop()


@pytest.mark.trio
@pytest.mark.parametrize(
    "task",
    [
        mocked_firmware_tasks(),
        mocked_app_tasks(),
        mocked_model_tasks(),
        mocked_config_tasks(),
    ],
)
async def test_isolate_firmware_failure(task: Task):
    errored_with(task, "Task failure")
    executor = TrioBackgroundTasks()
    async with executor.run_forever():
        await executor.add_task(task)
        await trio.sleep(0.005)

        assert task.get_state() == Status.ERROR
        assert task.get_state().error == "Task failure"
        await executor.stop()


@pytest.mark.trio
async def test_fail_on_timeout():
    # mocked task waits the timeout before set success
    success_after = TimeoutConfig(timeout_in_seconds=1)
    raise_timeout_fast = TimeoutConfig(
        pollin_interval_in_seconds=0.005, timeout_in_seconds=0.005
    )
    timeout_task = mocked_task(timeout=success_after)
    # this timeout is the timeout the tasks returns and must fail if that timeout is reached
    # In this scenario we want that we raise timeout before finish the task
    timeout_task.timeout.side_effect = [raise_timeout_fast]
    executor = TrioBackgroundTasks()
    async with executor.run_forever():

        await executor.add_task(timeout_task)
        await trio.sleep(0.01)
        await trio.sleep(0.02)

        assert timeout_task.get_state() == Status.ERROR
        assert timeout_task.get_state().error == "Timed out"
        await executor.stop()


@pytest.mark.trio
async def test_stop_all_tasks():
    executor = TrioBackgroundTasks()
    long_running_task = mocked_task()
    async with executor.run_forever():

        await executor.add_task(long_running_task)
        await trio.sleep(0.006)
        await executor.stop()
    assert long_running_task.stop.await_count >= 1


@pytest.mark.trio
async def test_stop_cancels_unresponsive_tasks():
    executor = TrioBackgroundTasks()
    long_running_task = mocked_task(
        TimeoutConfig(pollin_interval_in_seconds=10, timeout_in_seconds=10)
    )
    with trio.fail_after(1) as cancel_scope:
        async with executor.run_forever():

            await executor.add_task(long_running_task)
            await trio.sleep(0.006)
            await executor.stop()

    assert not cancel_scope.cancel_called


@pytest.mark.trio
async def test_stop_is_clean():
    executor = TrioBackgroundTasks()
    long_running_task = mocked_task(
        TimeoutConfig(pollin_interval_in_seconds=10, timeout_in_seconds=10)
    )
    try:
        with trio.fail_after(1):
            async with executor.run_forever():

                await executor.add_task(long_running_task)
                await trio.sleep(0.006)
                await executor.stop()
    except BaseException:
        raise AssertionError("Stop should not throw exception")


@pytest.mark.trio
async def test_stop_on_not_started():
    executor = TrioBackgroundTasks()
    try:
        await executor.stop()
    except BaseException:
        raise AssertionError("Stop should not throw exception")


@pytest.mark.trio
async def test_deny_same_task_twice():
    executor = TrioBackgroundTasks()
    state = CameraState(MagicMock(), MagicMock())
    subtask = FirmwareTask(state, MagicMock())

    state.mqtt_port.value = 1
    config_1 = ConfigTask(state, MagicMock(), DeploymentConfig())
    config_1._tasks.append(subtask)
    await executor.add_task(config_1)

    with pytest.raises(UserException) as e:
        config_2 = ConfigTask(state, MagicMock(), DeploymentConfig())
        config_2._tasks.append(subtask)
        await executor.add_task(config_2)

    assert str(e.value) == "Another task is already running on the device"

    assert len(executor.list()) == 1


@pytest.mark.trio
async def test_could_add_twice_if_finished():
    state = CameraState(MagicMock(), MagicMock())
    subtask = FirmwareTask(state, MagicMock())
    executor = TrioBackgroundTasks()

    state.mqtt_port.value = 1
    config = ConfigTask(state, MagicMock(), DeploymentConfig())
    config._tasks.append(subtask)
    await executor.add_task(config)

    subtask._task_state.set(Status.SUCCESS)

    await executor.add_task(config)
    subtask._task_state = TaskState()
    subtask._task_state.error_notification("Error")

    await executor.add_task(config)

    subtask._task_state = TaskState()

    with pytest.raises(UserException) as e:
        config_2 = ConfigTask(state, MagicMock(), DeploymentConfig())
        await executor.add_task(config_2)

    assert str(e.value) == "Another task is already running on the device"


@pytest.mark.trio
async def test_check_multiple_tasks_not_added_to_list():

    executor = TrioBackgroundTasks()
    state = CameraState(MagicMock(), MagicMock())
    state.mqtt_port.value = 1
    errors = 0

    async def add_task(task: ConfigTask) -> None:
        nonlocal errors
        try:
            await executor.add_task(task)
        except BaseException:
            errors = errors + 1

    async with trio.open_nursery() as nursery:
        for i in range(10):
            task = ConfigTask(state, MagicMock(), DeploymentConfig())
            subtask = FirmwareTask(state, MagicMock())
            task._tasks.append(subtask)
            nursery.start_soon(add_task, task)
    assert errors == 9

    num_running_tasks = 0
    num_total_tasks = 0
    for t in executor.list():
        assert t.task.get_state().status not in Status.ERROR
        if t.task.get_state().status in Status.INITIALIZING:
            num_running_tasks = num_running_tasks + 1
        num_total_tasks += 1

    assert num_running_tasks == 1
    assert num_total_tasks == 1


@pytest.mark.trio
@pytest.mark.parametrize("status", Status)
async def test_deny_same_task_twice_stop_if_running(status: Status):
    executor = TrioBackgroundTasks()
    running = mocked_task(TimeoutConfig(timeout_in_seconds=1))
    running.id = MagicMock(return_value="duplicated")
    await executor.add_task(running)

    duplicated = mocked_task(TimeoutConfig(timeout_in_seconds=1))
    duplicated.id = MagicMock(return_value="duplicated")
    try:
        running.task_state.status = Status.RUNNING
        duplicated.task_state.status = status
        await executor.add_task(duplicated)
    except UserException:
        pass

    if status == Status.RUNNING:
        duplicated.stop.assert_awaited_once()
    else:
        duplicated.stop.assert_not_awaited()
