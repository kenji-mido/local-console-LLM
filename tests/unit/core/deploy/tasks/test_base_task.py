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
from time import sleep

import pytest
from local_console.core.deploy.tasks.base_task import Status
from local_console.core.deploy.tasks.base_task import TaskState


@pytest.mark.parametrize("status", Status)
def test_task_status(status: Status) -> None:
    now = datetime.now()
    assert TaskState(status=status, started_at=now) == TaskState(
        status=status, started_at=now
    )

    assert TaskState(status=status, started_at=now) == status


def test_task_state() -> None:

    assert TaskState(status=Status.RUNNING) == Status.RUNNING
    now = datetime.now()
    assert TaskState(
        status=Status.ERROR, error="Some Error", started_at=now
    ) == TaskState(status=Status.ERROR, error="Some Error", started_at=now)
    assert not TaskState(
        status=Status.ERROR, error="Some Error", started_at=now
    ) == TaskState(status=Status.ERROR, error="Other Some Error", started_at=now)
    assert not TaskState(
        status=Status.SUCCESS, error=None, started_at=now
    ) == TaskState(status=Status.ERROR, error=None, started_at=now)
    assert not TaskState(
        status=Status.ERROR, error="Some Error", started_at=now
    ) == TaskState(
        status=Status.ERROR, error="Some Error", started_at=now + timedelta(hours=1)
    )


def test_task_state_stated_at() -> None:
    state1 = TaskState()
    sleep(0.001)
    state2 = TaskState()
    assert state1 != state2
    assert state2.started_at > state1.started_at
    assert state2.started_at - state1.started_at < timedelta(seconds=1)
