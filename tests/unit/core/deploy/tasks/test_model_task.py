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
from unittest.mock import MagicMock

import pytest
import trio
from local_console.core.camera.state import CameraState
from local_console.core.deploy.tasks.base_task import Status
from local_console.core.deploy.tasks.model_task import ModelTask
from local_console.core.schemas.schemas import ModelDeploymentConfig
from local_console.utils.trio import EVENT_WAITING

from tests.fixtures.agent import running_servers
from tests.strategies.samplers.files import FileInfoSampler
from tests.strategies.samplers.files import ModelSampler
from tests.strategies.samplers.mqtt_message import MockMQTTMessage


def _mocked_content(file: Path) -> bytearray:
    file_content = bytearray(64)
    file_content[0x30:0x40] = b"000000000000000"
    file.write_bytes(file_content)
    return file_content


def test_initialize() -> None:
    model = ModelSampler().sample()
    state = MagicMock(spec=CameraState)
    task = ModelTask(state, model)

    assert task.get_state() == Status.INITIALIZING


@pytest.mark.trio
async def test_task_starting() -> None:
    async def _ensure_not_finished(a: any, b: any, c: any) -> None:
        await trio.sleep(0.2)

    async with running_servers() as servers, trio.open_nursery() as nursery:
        with TemporaryDirectory() as tmp:
            model_file = Path(tmp) / "file.fpk"
            _mocked_content(model_file)
            model = ModelSampler(file=FileInfoSampler(path=model_file)).sample()

            task = ModelTask(servers.state, model)
            nursery.start_soon(task.run)
            await EVENT_WAITING.wait_for(
                lambda: task.get_state() != Status.INITIALIZING
            )
            nursery.cancel_scope.cancel()
    assert task.get_state() == Status.RUNNING


@pytest.mark.trio
async def test_task_success() -> None:
    async with running_servers() as servers:
        with TemporaryDirectory() as tmp:
            model_file = Path(tmp) / "file.fpk"
            file_content = _mocked_content(model_file)
            info = ModelSampler(file=FileInfoSampler(path=model_file)).sample()
            task = ModelTask(servers.state, info)
            async with trio.open_nursery() as nursery:
                nursery.start_soon(task.run)
                # wait for undeploy
                for i in range(100):
                    msg = MockMQTTMessage.config_status(
                        sensor_id=f"000A50{i}", dnn_model_version=[]
                    )
                    servers.mqtt.send_messages([msg])
                    if not servers.http.initialized_dir():
                        await trio.sleep(0.1)
                    else:
                        break
                server_dir: Path = servers.http.initialized_dir()
                served_file: Path = server_dir / "file.fpk"
                assert served_file.read_bytes() == file_content
                for i in range(100):
                    msg = MockMQTTMessage.config_status(
                        sensor_id=f"100A50{i}", dnn_model_version=["0308000000000100"]
                    )
                    servers.mqtt.send_messages([msg])
                    if task.get_state() == Status.SUCCESS:
                        break
                    await trio.sleep(0.01)
    assert task.get_state() == Status.SUCCESS


@pytest.mark.trio
async def test_task_stop_before_end() -> None:
    async with running_servers() as servers:
        with TemporaryDirectory() as tmp:
            model_file = Path(tmp) / "file.fpk"
            _mocked_content(model_file)
            info = ModelSampler(file=FileInfoSampler(path=model_file)).sample()
            task = ModelTask(servers.state, info)
            async with trio.open_nursery() as nursery:
                nursery.start_soon(task.run)
                await task.stop()
                nursery.cancel_scope.cancel()
    assert task.get_state().status == Status.ERROR
    assert task.get_state().error == "Task has been externally stopped"


def test_task_id() -> None:
    state = CameraState(MagicMock(), MagicMock())
    state.mqtt_port.value = 1
    task = ModelTask(state, MagicMock())
    assert task.id() == "model_task_for_device_1"


def test_task_id_needs_id() -> None:
    state = CameraState(MagicMock(), MagicMock())
    task = ModelTask(state, MagicMock())
    with pytest.raises(AssertionError) as e:
        task.id()
    assert str(e.value) == "Id of the camera is needed"


@pytest.mark.trio
async def test_timeout_on_undeploy() -> None:
    async with running_servers() as servers:
        with TemporaryDirectory() as tmp:
            model_file = Path(tmp) / "file.fpk"
            file_content = _mocked_content(model_file)
            info = ModelSampler(file=FileInfoSampler(path=model_file)).sample()
            task = ModelTask(
                servers.state,
                info,
                params=ModelDeploymentConfig(undeploy_timeout=0.01),
            )
            servers.state.device_config.value.OTA.UpdateStatus = "NotDone"
            async with trio.open_nursery() as nursery:
                nursery.start_soon(task.run)
                # undeploy timeout
                await trio.sleep(0.02)
                # wait for download file
                await EVENT_WAITING.wait_for(lambda: servers.http.initialized_dir())
                server_dir: Path = servers.http.initialized_dir()
                served_file: Path = server_dir / "file.fpk"
                assert served_file.read_bytes() == file_content
                for i in range(100):
                    msg = MockMQTTMessage.config_status(
                        sensor_id=f"100A50{i}", dnn_model_version=["0308000000000100"]
                    )
                    servers.mqtt.send_messages([msg])
                    if task.get_state() == Status.SUCCESS:
                        break
                    await trio.sleep(0.01)
    assert task.get_state() == Status.SUCCESS


@pytest.mark.trio
async def test_undeploy_failed_deploy_success() -> None:
    async with running_servers() as servers:
        with TemporaryDirectory() as tmp:
            model_file = Path(tmp) / "file.fpk"
            file_content = _mocked_content(model_file)
            info = ModelSampler(file=FileInfoSampler(path=model_file)).sample()
            task = ModelTask(servers.state, info)
            async with trio.open_nursery() as nursery:
                nursery.start_soon(task.run)
                # wait for undeploy
                for i in range(100):
                    msg = MockMQTTMessage.config_status(
                        sensor_id=f"000A50{i}",
                        dnn_model_version=[],
                        update_status="Failed",
                    )
                    servers.mqtt.send_messages([msg])
                    if not servers.http.initialized_dir():
                        await trio.sleep(0.1)
                    else:
                        break
                server_dir: Path = servers.http.initialized_dir()
                served_file: Path = server_dir / "file.fpk"
                assert served_file.read_bytes() == file_content
                for i in range(100):
                    msg = MockMQTTMessage.config_status(
                        sensor_id=f"100A50{i}", dnn_model_version=["0308000000000100"]
                    )
                    servers.mqtt.send_messages([msg])
                    if task.get_state() == Status.SUCCESS:
                        break
                    await trio.sleep(0.01)
    assert task.get_state() == Status.SUCCESS


@pytest.mark.trio
async def test_timeout_deploying() -> None:
    async with running_servers() as servers:
        with TemporaryDirectory() as tmp:
            model_file = Path(tmp) / "file.fpk"
            _mocked_content(model_file)
            info = ModelSampler(file=FileInfoSampler(path=model_file)).sample()
            task = ModelTask(
                servers.state,
                info,
                params=ModelDeploymentConfig(deploy_timeout=0.01),
            )
            async with trio.open_nursery() as nursery:
                nursery.start_soon(task.run)
                # wait for undeploy
                for i in range(100):
                    msg = MockMQTTMessage.config_status(
                        sensor_id=f"000A50{i}", dnn_model_version=[]
                    )
                    servers.mqtt.send_messages([msg])
                    if not servers.http.initialized_dir():
                        await trio.sleep(0.1)
                    else:
                        break
                await trio.sleep(0.02)
    assert task.get_state() == Status.ERROR


@pytest.mark.trio
async def test_error_on_deploy() -> None:
    async with running_servers() as servers:
        with TemporaryDirectory() as tmp:
            model_file = Path(tmp) / "file.fpk"
            file_content = _mocked_content(model_file)
            info = ModelSampler(file=FileInfoSampler(path=model_file)).sample()
            task = ModelTask(servers.state, info)
            async with trio.open_nursery() as nursery:
                nursery.start_soon(task.run)
                # wait for undeploy
                for i in range(100):
                    msg = MockMQTTMessage.config_status(
                        sensor_id=f"000A50{i}", dnn_model_version=[]
                    )
                    servers.mqtt.send_messages([msg])
                    if not servers.http.initialized_dir():
                        await trio.sleep(0.1)
                    else:
                        break
                server_dir: Path = servers.http.initialized_dir()
                served_file: Path = server_dir / "file.fpk"
                assert served_file.read_bytes() == file_content
                for i in range(100):
                    msg = MockMQTTMessage.config_status(
                        sensor_id=f"100A50{i}",
                        dnn_model_version=["0308000000000100"],
                        update_status="Failed",
                    )
                    servers.mqtt.send_messages([msg])
                    if task.get_state() == Status.ERROR:
                        break
                    await trio.sleep(0.01)
    assert task.get_state() == Status.ERROR
