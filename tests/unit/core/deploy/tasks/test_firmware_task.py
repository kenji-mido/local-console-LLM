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
from unittest.mock import patch

import pytest
import trio
from local_console.core.camera.enums import OTAUpdateStatus
from local_console.core.camera.firmware import FirmwareValidationStatus
from local_console.core.camera.state import CameraState
from local_console.core.deploy.tasks.base_task import Status
from local_console.core.deploy.tasks.firmware_task import FirmwareTask
from local_console.core.schemas.edge_cloud_if_v1 import DnnOta
from local_console.core.schemas.edge_cloud_if_v1 import DnnOtaBody
from local_console.utils.trio import EVENT_WAITING

from tests.fixtures.agent import running_servers
from tests.fixtures.firmware import mock_get_ota_update_status
from tests.strategies.samplers.files import FileInfoSampler
from tests.strategies.samplers.files import FirmwareInfoDTOSampler
from tests.strategies.samplers.files import FirmwareSampler
from tests.strategies.samplers.mqtt_message import MockMQTTMessage


def test_task_initializing() -> None:
    state = MagicMock()
    info = FirmwareInfoDTOSampler().sample()

    task = FirmwareTask(state, info)

    assert task.get_state() == Status.INITIALIZING


@pytest.mark.trio
async def test_task_starting() -> None:
    async def _ensure_not_finished(a: any, c: any) -> None:
        await trio.sleep(0.2)

    with patch(
        "local_console.core.deploy.tasks.firmware_task.update_firmware_task",
        new_callable=AsyncMock,
        side_effect=_ensure_not_finished,
    ):
        async with trio.open_nursery() as nursery:
            state = MagicMock()
            info = FirmwareSampler().sample()

            task = FirmwareTask(state, info)
            nursery.start_soon(task.run)
            await EVENT_WAITING.wait_for(
                lambda: task.get_state() != Status.INITIALIZING
            )
            assert task.get_state() == Status.RUNNING


@pytest.mark.trio
async def test_task_success() -> None:
    async with running_servers() as servers:
        with (
            TemporaryDirectory() as tmp,
            mock_get_ota_update_status(
                [
                    OTAUpdateStatus.DONE,
                    OTAUpdateStatus.DOWNLOADING,
                    OTAUpdateStatus.DONE,
                ]
            ),
        ):
            firmware_file = Path(tmp) / "file.fpk"
            firmware_content = b"Sample content"
            firmware_file.write_bytes(firmware_content)
            info = FirmwareSampler(file=FileInfoSampler(path=firmware_file)).sample()
            task = FirmwareTask(servers.state, info)
            async with trio.open_nursery() as nursery:
                nursery.start_soon(task.run)
                await EVENT_WAITING.wait_for(
                    lambda: servers.http.initialized_dir() is not None
                )
                server_dir: Path = servers.http.initialized_dir()
                served_file: Path = server_dir / "file.fpk"
                assert served_file.read_bytes() == firmware_content
                for i in range(100):
                    msg = MockMQTTMessage.config_status(sensor_id=f"100A50{i}")
                    servers.mqtt.send_messages([msg])
                    if task.get_state() == Status.SUCCESS:
                        break
                    await trio.sleep(0.01)
            assert task.get_state() == Status.SUCCESS


@pytest.mark.trio
async def test_task_no_device_config() -> None:
    async with running_servers() as servers:
        info = FirmwareSampler().sample()
        task = FirmwareTask(servers.state, info)

        await task.run()
        assert task.get_state() == Status.ERROR
        assert task.get_state().error == "Firmware file does not exist!"


@pytest.mark.trio
async def test_task_stop_before_end() -> None:
    async with running_servers() as servers:
        with TemporaryDirectory() as tmp:
            firmware_file = Path(tmp) / "file.fpk"
            firmware_content = b"Sample content"
            firmware_file.write_bytes(firmware_content)
            info = FirmwareSampler(file=FileInfoSampler(path=firmware_file)).sample()
            task = FirmwareTask(servers.state, info)
            async with trio.open_nursery() as nursery:
                nursery.start_soon(task.run)
                await task.stop()
                nursery.cancel_scope.cancel()
    assert task.get_state().status == Status.ERROR
    assert task.get_state().error == "Task has been externally stopped"


def test_task_id() -> None:
    state = CameraState(MagicMock(), MagicMock())
    state.mqtt_port.value = 1
    task = FirmwareTask(state, MagicMock())
    assert task.id() == "firmware_task_for_device_1"


def test_task_id_needs_id() -> None:
    state = CameraState(MagicMock(), MagicMock())
    task = FirmwareTask(state, MagicMock())
    with pytest.raises(AssertionError) as e:
        task.id()
    assert str(e.value) == "Id of the camera is needed"


@pytest.mark.trio
@pytest.mark.parametrize("status", FirmwareValidationStatus)
async def test_validate_error_result_in_task_error(
    status: FirmwareValidationStatus,
) -> None:
    with (
        patch(
            "local_console.core.camera.firmware.process_firmware_file",
            return_value=(None, None),
        ),
        patch(
            "local_console.core.camera.firmware.configuration_spec",
            return_value=DnnOta(
                OTA=DnnOtaBody(
                    DesiredVersion="1",
                    PackageUri="1",
                    HashValue="1",
                )
            ),
        ),
        patch("local_console.core.camera.firmware.Agent") as agent,
        patch(
            "local_console.core.camera.firmware.validate_firmware_file",
            return_value=status,
        ) as validated,
    ):
        agent.return_value.configure = AsyncMock()
        expected_state = Status.ERROR
        if status == FirmwareValidationStatus.VALID:
            expected_state = Status.RUNNING
        async with trio.open_nursery() as nursery:
            state = CameraState(MagicMock(), MagicMock())
            state.mqtt_port.value = 1883
            info = FirmwareSampler().sample()

            task = FirmwareTask(state, info)
            nursery.start_soon(task.run)
            await EVENT_WAITING.wait_for(lambda: validated.call_count > 0)
            assert task.get_state() == expected_state
            nursery.cancel_scope.cancel()


@pytest.mark.trio
async def test_device_send_error() -> None:
    async with running_servers() as servers:
        with TemporaryDirectory() as tmp:
            firmware_file = Path(tmp) / "file.fpk"
            firmware_content = b"Sample content"
            firmware_file.write_bytes(firmware_content)
            info = FirmwareSampler(file=FileInfoSampler(path=firmware_file)).sample()
            task = FirmwareTask(servers.state, info)
            async with trio.open_nursery() as nursery:
                nursery.start_soon(task.run)
                await EVENT_WAITING.wait_for(
                    lambda: servers.http.initialized_dir() is not None
                )
                server_dir: Path = servers.http.initialized_dir()
                served_file: Path = server_dir / "file.fpk"
                assert served_file.read_bytes() == firmware_content
                for i in range(100):
                    msg = MockMQTTMessage.config_status(
                        sensor_id=f"100A50{i}", update_status="Failed"
                    )
                    servers.mqtt.send_messages([msg])
                    if task.get_state() == Status.ERROR:
                        break
                    await trio.sleep(0.01)
            assert task.get_state() == Status.ERROR
