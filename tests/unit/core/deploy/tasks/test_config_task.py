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
from datetime import datetime
from datetime import timedelta
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from local_console.core.camera.state import CameraState
from local_console.core.deploy.tasks.base_task import Status
from local_console.core.deploy.tasks.base_task import Task
from local_console.core.deploy.tasks.base_task import TaskState
from local_console.core.deploy.tasks.config_task import ConfigTask
from local_console.core.schemas.schemas import DeploymentConfig
from local_console.utils.trio import DEFAULT_TASK_TIMEOUT
from local_console.utils.trio import TimeoutConfig

from tests.mocks.tasks import mocked_app_tasks
from tests.mocks.tasks import mocked_firmware_tasks
from tests.mocks.tasks import mocked_model_tasks
from tests.strategies.samplers.files import DeployConfigSampler


def task_with_state(state: TaskState) -> Task:
    mocked_task = MagicMock(spec=Task)
    mocked_task.get_state.return_value = state
    mocked_task.return_value.get_state.return_value = state
    mocked_task.return_value.run = AsyncMock()
    mocked_task.return_value.stop = AsyncMock()
    return mocked_task


def task_with_status(status: Status) -> Task:
    return task_with_state(TaskState(status=status))


@pytest.mark.trio
async def test_task_empty_config() -> None:
    state = MagicMock(spec=CameraState)
    config = DeployConfigSampler(firmware=None, num_apps=0, num_models=0).sample()
    task = ConfigTask(state, config, DeploymentConfig())

    await task.run()

    assert task.get_state() == Status.SUCCESS


@pytest.mark.trio
async def test_task_success() -> None:
    mocked_task = task_with_status(Status.SUCCESS)
    with (
        patch("local_console.core.deploy.tasks.config_task.AppTask", mocked_task),
        patch("local_console.core.deploy.tasks.config_task.FirmwareTask", mocked_task),
        patch("local_console.core.deploy.tasks.config_task.ModelTask", mocked_task),
    ):
        state = MagicMock(spec=CameraState)
        config = DeployConfigSampler(num_apps=1, num_models=1).sample()
        task = ConfigTask(state, config, DeploymentConfig())

        await task.run()

        assert task.get_state() == Status.SUCCESS
        assert mocked_task.return_value.run.await_count == 3


@pytest.mark.trio
async def test_task_not_stop_on_error() -> None:
    mocked_task = task_with_status(Status.SUCCESS)
    errored_task = task_with_status(Status.ERROR)
    with (
        patch("local_console.core.deploy.tasks.config_task.FirmwareTask", mocked_task),
        patch("local_console.core.deploy.tasks.config_task.AppTask", errored_task),
        patch("local_console.core.deploy.tasks.config_task.ModelTask", mocked_task),
    ):
        state = MagicMock(spec=CameraState)
        config = DeployConfigSampler(num_apps=1, num_models=1).sample()
        task = ConfigTask(state, config, DeploymentConfig())

        await task.run()

        assert task.get_state() == Status.ERROR
        assert mocked_task.return_value.run.await_count == 2
        assert errored_task.return_value.run.await_count == 1


@pytest.mark.parametrize(
    "tasks,status",
    [
        [[task_with_status(Status.INITIALIZING)], Status.INITIALIZING],
        [
            [
                task_with_status(Status.INITIALIZING),
                task_with_status(Status.INITIALIZING),
                task_with_status(Status.INITIALIZING),
            ],
            Status.INITIALIZING,
        ],
        [[], Status.SUCCESS],
        [[task_with_status(Status.SUCCESS)], Status.SUCCESS],
        [
            [
                task_with_status(Status.SUCCESS),
                task_with_status(Status.SUCCESS),
                task_with_status(Status.SUCCESS),
            ],
            Status.SUCCESS,
        ],
        [
            [
                task_with_status(Status.ERROR),
                task_with_status(Status.RUNNING),
                task_with_status(Status.SUCCESS),
            ],
            Status.ERROR,
        ],
        [[task_with_status(Status.ERROR)], Status.ERROR],
        [
            [
                task_with_status(Status.RUNNING),
                task_with_status(Status.ERROR),
                task_with_status(Status.RUNNING),
            ],
            Status.ERROR,
        ],
        [
            [
                task_with_status(Status.INITIALIZING),
                task_with_status(Status.RUNNING),
                task_with_status(Status.SUCCESS),
            ],
            Status.RUNNING,
        ],
        [
            [
                task_with_status(Status.INITIALIZING),
                task_with_status(Status.SUCCESS),
                task_with_status(Status.SUCCESS),
            ],
            Status.RUNNING,
        ],
    ],
)
def test_get_status_from_tasks(tasks: list[Task], status: Status) -> None:
    task = ConfigTask(MagicMock(), MagicMock(), DeploymentConfig())
    task._tasks = tasks
    assert task.get_state() == status


now = datetime.now()


@pytest.mark.parametrize(
    "tasks,state",
    [
        [
            [
                task_with_state(TaskState(status=Status.SUCCESS, started_at=now)),
                task_with_state(
                    TaskState(
                        status=Status.SUCCESS, started_at=now + timedelta(seconds=1)
                    )
                ),
                task_with_state(
                    TaskState(
                        status=Status.SUCCESS, started_at=now + timedelta(seconds=2)
                    )
                ),
            ],
            TaskState(status=Status.SUCCESS, started_at=now),
        ],
        [
            [
                task_with_state(TaskState(status=Status.ERROR, started_at=now)),
                task_with_state(
                    TaskState(
                        status=Status.ERROR, started_at=now + timedelta(seconds=1)
                    )
                ),
                task_with_state(
                    TaskState(
                        status=Status.ERROR, started_at=now + timedelta(seconds=2)
                    )
                ),
            ],
            TaskState(status=Status.ERROR, started_at=now),
        ],
        [
            [
                task_with_state(TaskState(status=Status.SUCCESS, started_at=now)),
                task_with_state(
                    TaskState(
                        status=Status.SUCCESS, started_at=now + timedelta(seconds=1)
                    )
                ),
                task_with_state(
                    TaskState(
                        status=Status.RUNNING, started_at=now + timedelta(seconds=2)
                    )
                ),
            ],
            TaskState(status=Status.RUNNING, started_at=now),
        ],
        [
            [
                task_with_state(TaskState(status=Status.RUNNING, started_at=now)),
                task_with_state(
                    TaskState(
                        status=Status.ERROR, started_at=now + timedelta(seconds=1)
                    )
                ),
                task_with_state(
                    TaskState(
                        status=Status.RUNNING, started_at=now + timedelta(seconds=2)
                    )
                ),
            ],
            TaskState(status=Status.ERROR, started_at=now),
        ],
    ],
)
def test_get_state_with_datetime(tasks: list[Task], state: TaskState):
    task = ConfigTask(MagicMock(), MagicMock(), DeploymentConfig())
    task._tasks = tasks
    assert task.get_state() == state


def test_errored_call_all_subtask() -> None:
    task = ConfigTask(MagicMock(), MagicMock(), DeploymentConfig())
    task._tasks = [mocked_firmware_tasks(), mocked_app_tasks(), mocked_model_tasks()]

    exception = Exception("Test Error")
    task.errored(exception)

    for subtask in task._tasks:
        assert subtask.get_state() == Status.ERROR
    assert task.get_state() == Status.ERROR
    assert task.get_state().error == str(exception)


def test_errored_test_timeout() -> None:
    task = ConfigTask(MagicMock(), MagicMock(), DeploymentConfig())
    task._tasks = [mocked_firmware_tasks(), mocked_app_tasks(), mocked_model_tasks()]

    assert task.timeout() == TimeoutConfig(
        pollin_interval_in_seconds=DEFAULT_TASK_TIMEOUT.pollin_interval_in_seconds * 3,
        timeout_in_seconds=DEFAULT_TASK_TIMEOUT.timeout_in_seconds * 3,
    )


@pytest.mark.trio
async def test_task_stop_before_end() -> None:
    running_task = task_with_status(Status.RUNNING)
    with (
        patch("local_console.core.deploy.tasks.config_task.AppTask", running_task),
        patch("local_console.core.deploy.tasks.config_task.FirmwareTask", running_task),
        patch("local_console.core.deploy.tasks.config_task.ModelTask", running_task),
    ):
        state = MagicMock(spec=CameraState)
        config = DeployConfigSampler(num_apps=1, num_models=1).sample()
        task = ConfigTask(state, config, DeploymentConfig())

        await task.stop()

        assert running_task.return_value.stop.await_count == 3


@pytest.mark.trio
async def test_task_not_stop_if_not_running() -> None:
    init_task = task_with_status(Status.INITIALIZING)
    success_task = task_with_status(Status.SUCCESS)
    error_task = task_with_status(Status.SUCCESS)
    with (
        patch("local_console.core.deploy.tasks.config_task.AppTask", init_task),
        patch("local_console.core.deploy.tasks.config_task.FirmwareTask", success_task),
        patch("local_console.core.deploy.tasks.config_task.ModelTask", error_task),
    ):
        state = MagicMock(spec=CameraState)
        config = DeployConfigSampler(num_apps=1, num_models=1).sample()
        task = ConfigTask(state, config, DeploymentConfig())

        await task.stop()

        assert init_task.return_value.stop.await_count == 0
        assert success_task.return_value.stop.await_count == 0
        assert error_task.return_value.stop.await_count == 0


def test_task_id() -> None:
    state = CameraState(MagicMock(), MagicMock())
    state.mqtt_port.value = 1
    task = ConfigTask(state, MagicMock(), DeploymentConfig())
    assert task.id() == "config_task_for_device_1"


def test_task_id_needs_id() -> None:
    state = CameraState(MagicMock(), MagicMock())
    task = ConfigTask(state, MagicMock(), DeploymentConfig())
    with pytest.raises(AssertionError) as e:
        task.id()
    assert str(e.value) == "Id of the camera is needed"
