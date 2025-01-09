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
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest
import trio
from local_console.core.camera.enums import DeployStage
from local_console.core.camera.state import CameraState
from local_console.core.deploy.tasks.app_task import AppTask
from local_console.core.deploy.tasks.base_task import Status
from local_console.utils.trio import EVENT_WAITING
from local_console.utils.trio import TimeoutConfig

from tests.fixtures.agent import running_servers
from tests.strategies.samplers.files import EdgeAppSampler
from tests.strategies.samplers.files import FileInfoSampler
from tests.strategies.samplers.mqtt_message import MockMQTTMessage


@pytest.mark.trio
async def test_task_starting() -> None:

    async with trio.open_nursery() as nursery, running_servers() as servers:
        with TemporaryDirectory() as tmp:
            file = Path(tmp) / "app.bin"
            file.write_bytes(b"dummy")
            app = EdgeAppSampler(file=FileInfoSampler(path=file)).sample()
            task = AppTask(servers.state, app)
            assert task.get_state() == Status.INITIALIZING
            nursery.start_soon(task.run)
            await EVENT_WAITING.wait_for(
                lambda: task.get_state() != Status.INITIALIZING
            )
            nursery.cancel_scope.cancel()
    assert task.get_state() == Status.RUNNING


def _get_id(state: CameraState) -> str:
    if not state._deploy_fsm or not state._deploy_fsm._to_deploy:
        return "0"
    return state._deploy_fsm._to_deploy.deployment.deploymentId


@pytest.mark.trio
async def test_task_success() -> None:
    async with trio.open_nursery() as nursery, running_servers() as servers:
        with TemporaryDirectory() as tmp:
            file = Path(tmp) / "app.bin"
            file.write_bytes(b"dummy")
            app = EdgeAppSampler(file=FileInfoSampler(path=file)).sample()
            task = AppTask(servers.state, app)
            nursery.start_soon(task.run)
            await EVENT_WAITING.wait_for(
                lambda: servers.http.external_set_dir() is not None
            )
            server_dir: Path = servers.http.external_set_dir()
            assert server_dir == file.parent
            for _ in range(200):
                find_the_id = _get_id(servers.state)
                msg = MockMQTTMessage.update_status(deployment_id=find_the_id)
                servers.mqtt.send_messages([msg])
                if task.get_state() not in [Status.SUCCESS, Status.ERROR]:
                    await trio.sleep(0.05)
                else:
                    break
            nursery.cancel_scope.cancel()
    assert task.get_state() == Status.SUCCESS


@pytest.mark.trio
async def test_task_error() -> None:
    async with trio.open_nursery() as nursery, running_servers() as servers:
        with TemporaryDirectory() as tmp:
            file = Path(tmp) / "app.bin"
            file.write_bytes(b"dummy")
            app = EdgeAppSampler(file=FileInfoSampler(path=file)).sample()
            task = AppTask(servers.state, app)
            nursery.start_soon(task.run)
            for _ in range(200):
                find_the_id = _get_id(servers.state)
                msg = MockMQTTMessage.update_status(
                    deployment_id=find_the_id,
                    status="error",
                    modules={"module_name": {"status": "error"}},
                )
                servers.mqtt.send_messages([msg])
                if task.get_state() not in [Status.SUCCESS, Status.ERROR]:
                    await trio.sleep(0.05)
                else:
                    break
            nursery.cancel_scope.cancel()
    assert task.get_state() == Status.ERROR
    assert task.get_state().error is None


@pytest.mark.trio
async def test_task_timeout() -> None:
    timeout = TimeoutConfig(timeout_in_seconds=0.005, pollin_interval_in_seconds=0.005)

    async with trio.open_nursery() as nursery, running_servers() as servers:
        with TemporaryDirectory() as tmp:
            file = Path(tmp) / "app.bin"
            file.write_bytes(b"dummy")
            app = EdgeAppSampler(file=FileInfoSampler(path=file)).sample()
            task = AppTask(servers.state, app, timeout=timeout)
            nursery.start_soon(task.run)
            for _ in range(10):
                if task.get_state() not in [Status.SUCCESS, Status.ERROR]:
                    await trio.sleep(0.05)
                else:
                    break
            nursery.cancel_scope.cancel()
    assert task.get_state() == Status.ERROR
    assert (
        task.get_state().error
        == f"Could not deploy app {app.info.edge_app_package_id} in {timeout.timeout_in_seconds} seconds."
    )


def test_task_default_timeout() -> None:
    assert AppTask(None, None).timeout().timeout_in_seconds >= 600


@pytest.mark.trio
async def test_task_unsubscribe_on_success() -> None:
    state = AsyncMock()
    app = EdgeAppSampler().sample()
    task = AppTask(state, app)
    task._task_state.set(Status.SUCCESS)
    await task.run()
    state.deploy_stage.subscribe_async.assert_called_once_with(task._change_state)
    state.deploy_stage.unsubscribe_async.assert_called_once_with(task._change_state)


@pytest.mark.trio
async def test_task_unsubscribe_on_error() -> None:
    state = AsyncMock()
    app = EdgeAppSampler().sample()
    task = AppTask(state, app)
    state.do_app_deployment.side_effect = Exception("Unexpected error")
    with pytest.raises(Exception):
        await task.run()
    state.deploy_stage.subscribe_async.assert_called_once_with(task._change_state)
    state.deploy_stage.unsubscribe_async.assert_called_once_with(task._change_state)


@pytest.mark.trio
async def test_task_change_state_inputs() -> None:
    state = AsyncMock()
    app = EdgeAppSampler().sample()
    task = AppTask(state, app)
    task._task_state.set(Status.RUNNING)
    await task._change_state(DeployStage.WaitAppliedConfirmation, None)
    assert task._task_state.get() == Status.RUNNING
    await task._change_state(None, DeployStage.WaitAppliedConfirmation)
    assert task._task_state.get() == Status.RUNNING
    await task._change_state(
        DeployStage.WaitFirstStatus, DeployStage.WaitAppliedConfirmation
    )
    assert task._task_state.get() == Status.RUNNING
    await task._change_state(DeployStage.Done, DeployStage.WaitFirstStatus)
    assert task._task_state.get() == Status.SUCCESS
    for stage in DeployStage:
        await task._change_state(stage, None)
        assert task._task_state.get() == Status.SUCCESS
        await task._change_state(None, stage)
        assert task._task_state.get() == Status.SUCCESS
    await task._change_state(None, None)
    assert task._task_state.get() == Status.SUCCESS
    task = AppTask(state, app)
    await task._change_state(DeployStage.Error, None)
    assert task._task_state.get() == Status.ERROR
    for stage in DeployStage:
        await task._change_state(stage, None)
        assert task._task_state.get() == Status.ERROR
        await task._change_state(None, stage)
        assert task._task_state.get() == Status.ERROR
    await task._change_state(None, None)
    assert task._task_state.get() == Status.ERROR


@pytest.mark.trio
async def test_stop_task_before_ending() -> None:
    async with trio.open_nursery() as nursery, running_servers() as servers:
        with TemporaryDirectory() as tmp:
            file = Path(tmp) / "app.bin"
            file.write_bytes(b"dummy")
            app = EdgeAppSampler(file=FileInfoSampler(path=file)).sample()
            task = AppTask(servers.state, app)
            nursery.start_soon(task.run)
            await task.stop()
            await EVENT_WAITING.wait_for(
                lambda: task.get_state().status == Status.ERROR
            )

    assert task.get_state().status == Status.ERROR
    assert task.get_state().error == "Task has been externally stopped"


def test_task_id() -> None:
    state = CameraState(MagicMock(), MagicMock())
    state.mqtt_port.value = 1
    task = AppTask(state, MagicMock())
    assert task.id() == "app_task_for_device_1"


def test_task_id_needs_id() -> None:
    state = CameraState(MagicMock(), MagicMock())
    task = AppTask(state, MagicMock())
    with pytest.raises(AssertionError) as e:
        task.id()
    assert str(e.value) == "Id of the camera is needed"
