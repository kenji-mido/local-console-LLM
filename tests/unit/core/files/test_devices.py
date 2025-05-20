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
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from local_console.core.camera.states.v1.streaming import StreamingCameraV1
from local_console.core.camera.streaming import image_dir_for
from local_console.core.config import Config
from local_console.core.device_services import DeviceServices
from local_console.core.files.device import ImageFileManager
from local_console.core.files.device import InferenceFileManager
from local_console.core.files.exceptions import FileNotFound
from local_console.core.schemas.schemas import DeviceID

from tests.fixtures.devices import unmocked_device_service
from tests.mocks.config import set_configuration
from tests.mocks.devices import cs_init_context
from tests.strategies.samplers.configs import GlobalConfigurationSampler
from tests.strategies.samplers.device_config import DeviceConfigurationSampler

config_obj = Config()


@asynccontextmanager
async def device_services_and_state(
    base_path: Path,
) -> AsyncGenerator[tuple[DeviceServices, DeviceID], None]:
    simple_gconf = GlobalConfigurationSampler(num_of_devices=1).sample()
    device_conn_conf = simple_gconf.devices[0]
    device_id = device_conn_conf.id
    set_configuration(simple_gconf)
    async with (
        unmocked_device_service() as device_svc,
        cs_init_context(
            mqtt_host=device_conn_conf.mqtt.host,
            mqtt_port=device_conn_conf.mqtt.port,
            device_config=DeviceConfigurationSampler().sample(),
        ) as camera,
    ):
        device_svc.set_camera(device_id, camera)
        config_obj.update_persistent_attr(device_id, "device_dir_path", base_path)

        camera._state = StreamingCameraV1(camera._common_properties, {}, {})
        camera._state._ensure_directories()

        yield device_svc, device_id


@pytest.mark.trio
async def test_list_images(tmp_path) -> None:
    async with device_services_and_state(tmp_path) as (device_services, dev_id):
        image_dir = image_dir_for(dev_id)
        files = [image_dir / "file_1.jpg", image_dir / "file_2.jpg"]
        for file in files:
            file.write_text("content")
        subdir = image_dir / "subdir"
        subdir.mkdir()

        manager = ImageFileManager(device_services)
        infos = manager.list_for(dev_id)

        assert sorted(infos) == sorted(files)


@pytest.mark.trio
async def test_device_not_found(tmp_path) -> None:
    async with device_services_and_state(tmp_path) as (device_services, _):
        manager = ImageFileManager(device_services)
        with pytest.raises(FileNotFound) as error:
            manager.list_for(1)

        assert str(error.value) == "Device for port 1 not found"


@pytest.mark.trio
async def test_path_does_not_exists(tmp_path) -> None:
    async with device_services_and_state(tmp_path) as (
        device_services,
        dev_id,
    ):
        config_obj.get_device_config(dev_id).persist.device_dir_path = Path(
            "/dir/does/not/exist"
        )

        manager = ImageFileManager(device_services)

        with pytest.raises(FileNotFoundError) as error:
            manager.list_for(dev_id)

        assert "/dir/does/not/exist" in str(error.value)


@pytest.mark.trio
async def test_path_not_set(tmp_path) -> None:
    async with device_services_and_state(tmp_path) as (
        device_services,
        dev_id,
    ):
        config_obj.get_device_config(dev_id).persist.device_dir_path = None

        manager = ImageFileManager(device_services)
        with pytest.raises(AssertionError) as error:
            manager.list_for(dev_id)

        assert str(error.value) == f"Image folder not set for device {dev_id}"


@pytest.mark.trio
async def test_get_file(tmp_path) -> None:
    async with device_services_and_state(tmp_path) as (
        device_services,
        dev_id,
    ):
        file_name = "file_1.jpg"
        file = image_dir_for(dev_id) / file_name
        file.write_text("content")

        manager = ImageFileManager(device_services)
        result = manager.get_file(dev_id, file_name)

        assert result.read_text() == "content"


@pytest.mark.trio
async def test_get_file_not_found(tmp_path) -> None:
    async with device_services_and_state(tmp_path) as (
        device_services,
        dev_id,
    ):
        manager = ImageFileManager(device_services)
        with pytest.raises(FileNotFound) as error:
            manager.get_file(dev_id, "invalid.file")

        assert str(error.value) == "File 'invalid.file' does not exist"


@pytest.mark.trio
async def test_get_file_is_dir(tmp_path) -> None:
    async with device_services_and_state(tmp_path) as (
        device_services,
        dev_id,
    ):
        dir_name = "subdir"
        dir_ = image_dir_for(dev_id) / dir_name
        dir_.mkdir()

        manager = ImageFileManager(device_services)
        with pytest.raises(FileNotFound) as error:
            manager.get_file(dev_id, dir_name)

        assert str(error.value) == "File 'subdir' does not exist"


@pytest.mark.trio
async def test_inference_path_not_set(tmp_path) -> None:
    async with device_services_and_state(tmp_path) as (
        device_services,
        dev_id,
    ):
        config_obj.get_device_config(dev_id).persist.device_dir_path = None

        manager = InferenceFileManager(device_services)
        with pytest.raises(AssertionError) as error:
            manager.list_for(dev_id)

        assert str(error.value) == f"Inference folder not set for device {dev_id}"
