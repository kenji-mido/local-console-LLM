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
from local_console.core.camera.state import CameraState
from local_console.core.device_services import DeviceServices
from local_console.core.files.device import ImageFileManager
from local_console.core.files.device import InferenceFileManager
from local_console.core.files.exceptions import FileNotFound
from local_console.utils.tracking import TrackingVariable

from tests.mocks.devices import mocked_device_services


def device_services_and_state(
    image_path: Path | None = None, inference_path: Path | None = None
) -> tuple[DeviceServices, CameraState]:
    device_id = 1883
    device_services = mocked_device_services()
    camera_state = CameraState(MagicMock(), MagicMock())
    camera_state.mqtt_port.value = device_id
    device_services.states[device_id] = camera_state
    if image_path:
        camera_state.image_dir_path.value = image_path
    if inference_path:
        camera_state.inference_dir_path.value = inference_path
    return [device_services, camera_state]


def test_list_images() -> None:
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        base_path = Path(temporary_dir)
        files = [base_path / "file_1.jpg", base_path / "file_2.jpg"]
        for file in files:
            file.write_text("content")
        subdir = base_path / "subdir"
        subdir.mkdir()

        device_services, camera_state = device_services_and_state(image_path=base_path)

        manager = ImageFileManager(device_services)

        infos = manager.list_for(camera_state.mqtt_port.value)

        assert sorted(infos) == sorted(files)


def test_device_not_found() -> None:
    device_services, _ = device_services_and_state()

    manager = ImageFileManager(device_services)

    with pytest.raises(FileNotFound) as error:
        manager.list_for(1)

    assert str(error.value) == "Device for port 1 not found"


def test_path_does_not_exists() -> None:
    device_services, camera_state = device_services_and_state()
    camera_state.image_dir_path = TrackingVariable(Path("/dir/does/not/exists"))

    manager = ImageFileManager(device_services)

    with pytest.raises(FileNotFoundError) as error:
        manager.list_for(camera_state.mqtt_port.value)

    assert "/dir/does/not/exists" in str(error.value)


def test_path_not_set() -> None:
    device_services, camera_state = device_services_and_state()

    manager = ImageFileManager(device_services)

    with pytest.raises(AssertionError) as error:
        manager.list_for(camera_state.mqtt_port.value)

    assert (
        str(error.value)
        == f"There is not image folder for device {camera_state.mqtt_port.value}"
    )


def test_get_file() -> None:
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        base_path = Path(temporary_dir)
        file_name = "file_1.jpg"
        file = base_path / file_name
        file.write_text("content")
        device_services, camera_state = device_services_and_state(image_path=base_path)

        manager = ImageFileManager(device_services)

        result = manager.get_file(camera_state.mqtt_port.value, file_name)

        assert result.read_text() == "content"


def test_get_file_not_found() -> None:
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        device_services, camera_state = device_services_and_state(
            image_path=Path(temporary_dir)
        )

        manager = ImageFileManager(device_services)

        with pytest.raises(FileNotFound) as error:
            manager.get_file(camera_state.mqtt_port.value, "invalid.file")

        assert str(error.value) == "File 'invalid.file' does not exist"


def test_get_file_is_dir() -> None:
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        base_path = Path(temporary_dir)
        dir_name = "subdir"
        dir = base_path / dir_name
        dir.mkdir()
        device_services, camera_state = device_services_and_state(
            image_path=Path(temporary_dir)
        )

        manager = ImageFileManager(device_services)

        with pytest.raises(FileNotFound) as error:
            manager.get_file(camera_state.mqtt_port.value, dir_name)

        assert str(error.value) == "File 'subdir' does not exist"


def test_inference_path_not_set() -> None:
    device_services, camera_state = device_services_and_state()

    manager = InferenceFileManager(device_services)

    with pytest.raises(AssertionError) as error:
        manager.list_for(camera_state.mqtt_port.value)

    assert (
        str(error.value)
        == f"There is not inference folder for device {camera_state.mqtt_port.value}"
    )
