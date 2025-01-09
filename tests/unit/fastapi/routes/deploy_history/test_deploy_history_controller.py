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
from collections.abc import Generator
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest
import trio
from fastapi import status
from fastapi.testclient import TestClient
from local_console.core.camera.state import CameraState
from local_console.core.deploy.tasks.app_task import AppTask
from local_console.core.deploy.tasks.base_task import Status
from local_console.core.deploy.tasks.base_task import Task
from local_console.core.deploy.tasks.config_task import ConfigTask
from local_console.core.deploy.tasks.firmware_task import FirmwareTask
from local_console.core.deploy.tasks.model_task import ModelTask
from local_console.core.deploy.tasks.task_executors import TaskExecutor
from local_console.core.deploy.tasks.task_executors import TrioBackgroundTasks
from local_console.core.error.base import UserException
from local_console.core.schemas.schemas import DeploymentConfig
from local_console.fastapi.routes.deploy_history.controller import (
    DeployHistoryController,
)
from local_console.fastapi.routes.deploy_history.dependencies import (
    deploy_history_controller,
)
from local_console.fastapi.routes.deploy_history.dto import DeployHistory
from local_console.fastapi.routes.deploy_history.dto import DeployHistoryList

from tests.fixtures.fastapi import fa_client
from tests.strategies.samplers.deploy import DeployHistorySampler
from tests.strategies.samplers.deploy import TaskEntitySampler
from tests.strategies.samplers.files import DeployConfigSampler
from tests.strategies.samplers.files import EdgeAppSampler
from tests.strategies.samplers.files import FirmwareSampler
from tests.strategies.samplers.files import ModelSampler

earliest = datetime(1970, 1, 1, 0, 0, 0)


def task_to_deployhistory() -> Generator[Task, DeployHistory]:
    state = MagicMock()
    deploy_config = DeployConfigSampler(num_apps=1, num_models=1).sample()
    deploy_task = ConfigTask(
        state=state, config=deploy_config, params=DeploymentConfig()
    )
    deploy_task._tasks[0].get_state().started_at = earliest
    expected = DeployHistorySampler(
        deploy_type="ConfigTask",
        success_cnt=0,
        deploying_cnt=3,
        from_datetime=earliest,
        deploy_config=deploy_config,
    ).sample()
    expected.edge_system_sw_package[0].status = Status.INITIALIZING
    expected.edge_apps[0].status = Status.INITIALIZING
    expected.models[0].status = Status.INITIALIZING
    yield (deploy_task, expected)

    deploy_config = DeployConfigSampler(num_apps=3, num_models=3).sample()
    deploy_task = ConfigTask(
        state=state, config=deploy_config, params=DeploymentConfig()
    )
    expected = DeployHistorySampler(
        deploy_type="ConfigTask",
        fail_cnt=2,
        success_cnt=3,
        deploying_cnt=2,
        from_datetime=earliest,
        deploy_config=deploy_config,
    ).sample()
    deploy_task._tasks[0]._task_state.started_at = earliest

    task_status = [
        Status.SUCCESS,
        Status.RUNNING,
        Status.SUCCESS,
        Status.ERROR,
        Status.INITIALIZING,
        Status.ERROR,
        Status.SUCCESS,
    ]
    for i, stat in enumerate(task_status):
        deploy_task._tasks[i]._task_state.set(stat)

    expected.edge_system_sw_package[0].status = Status.SUCCESS

    for edge_app, stat in zip(
        expected.edge_apps, task_status[1 : 1 + len(expected.edge_apps)]
    ):
        edge_app.status = stat

    for model, stat in zip(expected.models, task_status[1 + len(expected.edge_apps) :]):
        model.status = stat

    yield (deploy_task, expected)
    deploy_config = DeployConfigSampler(num_apps=3, num_models=3).sample()
    deploy_task = ConfigTask(
        state=state, config=deploy_config, params=DeploymentConfig()
    )
    for task in deploy_task._tasks:
        task._task_state.set(Status.SUCCESS)
        task._task_state.started_at = earliest
    expected = DeployHistorySampler(
        deploy_type="ConfigTask",
        success_cnt=7,
        deploying_cnt=0,
        from_datetime=earliest,
        deploy_config=deploy_config,
    ).sample()
    expected.edge_system_sw_package[0].status = Status.SUCCESS
    for edge_app in expected.edge_apps:
        edge_app.status = Status.SUCCESS
    for model in expected.models:
        model.status = Status.SUCCESS

    yield (deploy_task, expected)
    input = FirmwareSampler().sample()
    task = FirmwareTask(state=state, firmware=input)
    task.get_state().started_at = earliest
    expected = DeployHistorySampler(
        deploy_type="FirmwareTask",
        success_cnt=0,
        deploying_cnt=1,
        from_datetime=earliest,
    ).sample()
    yield (task, expected)
    app = EdgeAppSampler().sample()
    task = AppTask(camera_state=state, app=app)
    task.get_state().started_at = earliest
    task._task_state.set(Status.SUCCESS)
    expected = DeployHistorySampler(
        deploy_type="AppTask",
        from_datetime=earliest,
    ).sample()
    yield (task, expected)
    input = ModelSampler().sample()
    task = ModelTask(state=state, model=input)
    task.get_state().started_at = earliest
    task._task_state.set(Status.SUCCESS)
    expected = DeployHistorySampler(
        deploy_type="ModelTask", success_cnt=0, fail_cnt=1, from_datetime=earliest
    ).sample()


@pytest.mark.parametrize("input, expected", task_to_deployhistory())
def test_task_to_deployhistory(input: Task, expected: DeployHistory) -> None:
    db = MagicMock(spec=TaskExecutor)
    controller = DeployHistoryController(tasks=db, deployment_manager=MagicMock())
    entity = TaskEntitySampler(id=expected.deploy_id, task=input).sample()

    result = controller._to_deploy_history(entity)
    assert result == expected


def test_deploy_history_datetime(fa_client: TestClient) -> None:
    controller = MagicMock()
    fa_client.app.dependency_overrides[deploy_history_controller] = lambda: controller

    element = DeployHistorySampler().sample()
    controller.get_list.return_value = DeployHistoryList(deploy_history=[element])

    result = fa_client.get("/deploy_history/")

    assert result.status_code == status.HTTP_200_OK
    from_datetime_str = result.json()["deploy_history"][0]["from_datetime"]

    assert datetime.fromisoformat(from_datetime_str) == element.from_datetime


def test_pagination(fa_client: TestClient) -> None:
    async def initialize() -> None:
        task_executor: TrioBackgroundTasks = fa_client.app.state.deploy_background_task
        for i in range(10):
            state = CameraState(MagicMock(), MagicMock())
            state.mqtt_port.value = 1883 + i
            deploy_config = DeployConfigSampler(config_id=f"{state.mqtt_port}").sample()
            deploy_task = ConfigTask(
                state=state, config=deploy_config, params=DeploymentConfig()
            )
            await task_executor.add_task(deploy_task)

    trio.run(initialize)

    result = fa_client.get("/deploy_history?limit=2")
    assert result.status_code == status.HTTP_200_OK
    history: list[dict[str, Any]] = result.json()["deploy_history"]
    assert [x["deploy_id"] for x in history] == [
        "config_task_for_device_1883",
        "config_task_for_device_1884",
    ]
    assert result.json()["continuation_token"] == "config_task_for_device_1884"

    result = fa_client.get(
        "/deploy_history?limit=2&starting_after=config_task_for_device_1884"
    )
    assert result.status_code == status.HTTP_200_OK
    history: list[dict[str, Any]] = result.json()["deploy_history"]
    assert [x["deploy_id"] for x in history] == [
        "config_task_for_device_1885",
        "config_task_for_device_1886",
    ]
    assert result.json()["continuation_token"] == "config_task_for_device_1886"


def test_task_running() -> None:
    task_executor: TrioBackgroundTasks = TrioBackgroundTasks()

    async def initialize() -> None:
        state = CameraState(MagicMock(), MagicMock())
        state.mqtt_port.value = 1883
        deploy_config = DeployConfigSampler(config_id=f"{state.mqtt_port}").sample()
        deploy_task = ConfigTask(
            state=state, config=deploy_config, params=DeploymentConfig()
        )
        await task_executor.add_task(deploy_task)
        with pytest.raises(UserException) as e:
            await task_executor.add_task(deploy_task)
        assert str(e.value) == "Another task is already running on the device"

    trio.run(initialize)

    deploy_history_controller = DeployHistoryController(
        tasks=task_executor, deployment_manager=MagicMock()
    )

    list_deploy_history: DeployHistoryList = deploy_history_controller.get_list()
    assert len(list_deploy_history.deploy_history) == 1
    assert len(list_deploy_history.deploy_history[0].edge_apps) == 1
    assert len(list_deploy_history.deploy_history[0].models) == 1
