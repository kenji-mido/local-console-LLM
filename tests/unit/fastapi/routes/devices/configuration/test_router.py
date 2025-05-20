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
from pathlib import Path
from random import randint
from unittest.mock import patch

import pytest
from fastapi import status
from httpx import AsyncClient
from local_console.core.camera.enums import ApplicationType
from local_console.core.camera.enums import UnitScale
from local_console.core.camera.machine import Camera
from local_console.core.camera.streaming import base_dir_for
from local_console.core.camera.streaming import image_dir_for
from local_console.core.camera.streaming import inference_dir_for
from local_console.core.config import Config
from local_console.core.device_services import DeviceConnection
from local_console.core.device_services import DeviceServices
from local_console.core.enums import ApplicationSchemaFilePath
from local_console.core.enums import DEFAULT_PERSIST_SETTINGS
from local_console.core.schemas.schemas import GlobalConfiguration
from local_console.core.schemas.utils import get_default_files_dir
from local_console.fastapi.main import lifespan
from local_console.fastapi.routes.devices.configuration.dto import (
    CameraConfigurationDTO,
)
from local_console.fastapi.routes.devices.configuration.dto import StatusType

from tests.fixtures.devices import stored_devices
from tests.mocks.mock_paho_mqtt import MockMqttAgent
from tests.strategies.samplers.configs import DeviceConnectionSampler


DeviceSetup = tuple[DeviceConnection, Camera, Config]


@pytest.fixture
async def device_setup(
    fa_client_async: AsyncClient,
    mocked_agent_fixture: MockMqttAgent,
    single_device_config: GlobalConfiguration,
) -> AsyncGenerator[tuple[DeviceSetup, Camera, Config], None]:
    config_obj = Config()
    device_conf = single_device_config.devices[0]
    device_id = device_conf.id

    app = fa_client_async._transport.app
    device_service = app.state.device_service
    async with (
        # The lifespan initializes the device specified in the config
        lifespan(app),
    ):
        camera = device_service.get_camera(device_id)
        yield device_conf, camera, config_obj


@pytest.mark.trio
async def test_get_configuration_exists_with_default_values(
    fa_client_async: AsyncClient, device_setup: DeviceSetup
) -> None:
    dev, _, _ = device_setup
    response = await fa_client_async.get(f"/devices/{dev.id}/configuration")
    assert response.status_code == 200

    payload = response.json()
    assert set(CameraConfigurationDTO.model_fields.keys()) == set(payload.keys())

    assert payload["device_dir_path"] is None
    assert payload["size"] == DEFAULT_PERSIST_SETTINGS.size
    assert payload["unit"] == DEFAULT_PERSIST_SETTINGS.unit
    assert payload["vapp_type"] == ApplicationType.IMAGE
    assert payload["vapp_config_file"] is None
    assert payload["vapp_labels_file"] is None


@pytest.mark.trio
async def test_get_configuration_exists_with_some_values(
    fa_client_async: AsyncClient, device_setup: DeviceSetup
) -> None:
    dev, _, config_obj = device_setup
    persist = config_obj.get_device_config(dev.id).persist
    persist.device_dir_path = Path("/tmp/files/base")
    persist.size = 5
    persist.unit = UnitScale.KB
    persist.vapp_type = ApplicationType.DETECTION
    persist.vapp_config_file = "/app/data/config"
    persist.vapp_labels_file = "/app/data/labels"

    response = await fa_client_async.get(f"/devices/{dev.id}/configuration")
    assert response.status_code == 200

    payload = response.json()
    assert set(CameraConfigurationDTO.model_fields.keys()) == set(payload.keys())

    assert payload["device_dir_path"] == "/tmp/files/base"
    assert payload["size"] == 5
    assert payload["unit"] == "KB"
    assert payload["vapp_type"] == "detection"
    assert payload["vapp_config_file"] == "/app/data/config"
    assert payload["vapp_labels_file"] == "/app/data/labels"


@pytest.mark.trio
async def test_get_configuration_invalid_unit_value(
    fa_client_async: AsyncClient, device_setup: DeviceSetup
) -> None:
    dev, _, config_obj = device_setup

    wrong_unit = "EiB"

    result = await fa_client_async.patch(
        f"/devices/{dev.id}/configuration",
        json={
            "unit": wrong_unit,
        },
    )

    assert result.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert result.json()["message"] == "EiB is not a valid unit"
    assert result.json()["code"] == "121001"

    result = await fa_client_async.get(f"/devices/{dev.id}/configuration")
    assert result.json()["unit"] == "MB"


@pytest.mark.trio
async def test_get_configuration_does_not_exist(
    fa_client_with_agent: AsyncClient, mocked_agent_fixture: MockMqttAgent
) -> None:
    expected_devices = DeviceConnectionSampler().list_of_samples()
    device_service: DeviceServices = (
        fa_client_with_agent._transport.app.state.device_service
    )
    async with stored_devices(expected_devices, device_service):

        response = await fa_client_with_agent.get("/devices/200000/configuration")
        payload = response.json()
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert payload["message"] == "Could not find device 200000"

        mocked_agent_fixture.stop_receiving_messages()


@pytest.mark.trio
async def test_update_happy_path(
    fa_client_async: AsyncClient, device_setup: DeviceSetup, tmp_path
) -> None:
    dev, _, config_obj = device_setup
    module_file = tmp_path / "module.signed.aot"
    ai_model_file = tmp_path / "detection.pkg"

    config_obj.get_device_config(dev.id).persist.device_dir_path = Path(
        "/something/expected/to/change"
    )

    result = await fa_client_async.patch(
        f"/devices/{dev.id}/configuration",
        json={
            "device_dir_path": str(tmp_path),
            "size": 6,
            "unit": "KB",
            "vapp_type": "detection",
            "vapp_config_file": "/vapp/config",
            "vapp_labels_file": "/vapp/labels",
            "module_file": str(module_file),
            "ai_model_file": str(ai_model_file),
        },
    )

    assert result.status_code == 200
    config_obj.read_config()
    device_config = config_obj.get_device_config(dev.id).persist
    assert device_config.device_dir_path == tmp_path
    assert device_config.size == 6
    assert device_config.unit == UnitScale.KB
    assert device_config.module_file == module_file
    assert device_config.ai_model_file == ai_model_file
    assert device_config.vapp_type == ApplicationType.DETECTION
    assert device_config.vapp_schema_file == str(ApplicationSchemaFilePath.DETECTION)
    assert device_config.vapp_config_file == "/vapp/config"
    assert device_config.vapp_labels_file == "/vapp/labels"


@pytest.mark.trio
async def test_update_individual_fields(
    fa_client_async: AsyncClient, device_setup: DeviceSetup, tmp_path
) -> None:
    dev, _, config_obj = device_setup

    persist = config_obj.get_device_config(dev.id).persist
    url = f"/devices/{dev.id}/configuration"

    assert persist.device_dir_path != tmp_path

    await fa_client_async.patch(url, json={"device_dir_path": str(tmp_path)})
    persist = config_obj.get_device_config(dev.id).persist
    assert persist.device_dir_path == tmp_path

    ai_model_file_path = tmp_path / "ai_model_file"
    assert persist.ai_model_file != ai_model_file_path

    await fa_client_async.patch(url, json={"ai_model_file": str(ai_model_file_path)})
    persist = config_obj.get_device_config(dev.id).persist
    assert persist.ai_model_file == ai_model_file_path

    module_file_path = tmp_path / "module_file"
    assert persist.module_file != module_file_path

    await fa_client_async.patch(url, json={"module_file": str(module_file_path)})
    persist = config_obj.get_device_config(dev.id).persist
    assert persist.module_file == module_file_path

    assert persist.size != 6

    await fa_client_async.patch(url, json={"size": 6})
    persist = config_obj.get_device_config(dev.id).persist
    assert persist.size == 6

    assert persist.unit != UnitScale.KB

    await fa_client_async.patch(url, json={"unit": "kB"})
    persist = config_obj.get_device_config(dev.id).persist
    assert persist.unit == UnitScale.KB

    await fa_client_async.patch(url, json={"vapp_type": "detection"})
    persist = config_obj.get_device_config(dev.id).persist
    actual_value = persist.vapp_type
    assert actual_value == ApplicationType.DETECTION

    expected_schema_file = getattr(ApplicationSchemaFilePath, "DETECTION")
    assert persist.vapp_schema_file == str(expected_schema_file)


@pytest.mark.trio
async def test_update_wrong_value(
    fa_client_async: AsyncClient, device_setup: DeviceSetup
) -> None:
    dev, dev_state, _ = device_setup

    result = await fa_client_async.patch(
        f"/devices/{dev.id}/configuration",
        json={
            "unit": "gigapascals",
        },
    )
    assert result.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "unit" in result.text


@pytest.mark.trio
async def test_update_unit_and_size_field(
    fa_client_async: AsyncClient, device_setup: DeviceSetup
) -> None:
    dev, camera, _ = device_setup

    assert camera._common_properties.dirs_watcher.current_limit != 123 * 1024
    result = await fa_client_async.patch(
        f"/devices/{dev.id}/configuration",
        json={
            "size": 123,
            "unit": "KB",
        },
    )
    assert result.status_code == status.HTTP_200_OK
    assert camera._common_properties.dirs_watcher.current_limit == 123 * 1024


@pytest.mark.trio
async def test_update_persists(
    fa_client_async: AsyncClient, device_setup: DeviceSetup, tmp_path
) -> None:

    dev, _, config_obj = device_setup
    dev_persistent = config_obj.get_device_config(dev.id)
    assert dev_persistent
    assert dev_persistent.persist.size != 123
    assert dev_persistent.persist.unit != UnitScale.KB
    assert dev_persistent.persist.module_file != Path("module/path")
    assert dev_persistent.persist.ai_model_file != Path("ai_model_file/path")
    assert dev_persistent.persist.device_dir_path != tmp_path

    await fa_client_async.patch(
        f"/devices/{dev.id}/configuration",
        json={
            "size": 123,
            "unit": "KB",
            "device_dir_path": str(tmp_path),
            "module_file": "module/path",
            "ai_model_file": "ai_model_file/path",
        },
    )
    config_obj.read_config()
    dev_persistent = config_obj.get_device_config(dev.id)
    assert dev_persistent.persist.size == 123
    assert dev_persistent.persist.unit == UnitScale.KB
    assert dev_persistent.persist.device_dir_path == tmp_path
    assert dev_persistent.persist.module_file == Path("module/path")
    assert dev_persistent.persist.ai_model_file == Path("ai_model_file/path")


@pytest.mark.trio
async def test_invalid_image_inference_path(
    fa_client_async: AsyncClient, device_setup: DeviceSetup
) -> None:
    dev, _, config_obj = device_setup

    result = await fa_client_async.patch(
        f"/devices/{dev.id}/configuration",
        json={
            "device_dir_path": "/",
        },
    )
    assert result.status_code == status.HTTP_200_OK
    assert StatusType.FOLDER_ERROR in result.json()["status"]

    device_path = get_default_files_dir() / "device"
    result = await fa_client_async.patch(
        f"/devices/{dev.id}/configuration",
        json={
            "device_dir_path": str(device_path),
        },
    )

    persist = config_obj.get_device_config(dev.id).persist
    assert persist.device_dir_path == device_path


@pytest.mark.trio
async def test_auto_deletion_flag(
    fa_client_async: AsyncClient, device_setup: DeviceSetup
) -> None:
    dev, _, config_obj = device_setup

    assert not config_obj.get_persistent_attr(dev.id, "auto_deletion")

    #  When parameter is True, value is updated
    result = await fa_client_async.patch(
        f"/devices/{dev.id}/configuration",
        json={
            "auto_deletion": True,
        },
    )
    assert result.status_code == 200
    assert config_obj.get_persistent_attr(dev.id, "auto_deletion")

    #  When parameter is not set, previous value is kept
    result = await fa_client_async.patch(
        f"/devices/{dev.id}/configuration",
        json={},
    )
    assert result.status_code == 200
    assert config_obj.get_persistent_attr(dev.id, "auto_deletion")

    #  When parameter is None, previous value is kept
    result = await fa_client_async.patch(
        f"/devices/{dev.id}/configuration",
        json={
            "auto_deletion": None,
        },
    )
    assert result.status_code == 200
    assert config_obj.get_persistent_attr(dev.id, "auto_deletion")

    #  When parameter is False, value is updated
    result = await fa_client_async.patch(
        f"/devices/{dev.id}/configuration",
        json={
            "auto_deletion": False,
        },
    )
    assert result.status_code == 200
    assert not config_obj.get_persistent_attr(dev.id, "auto_deletion")


@pytest.mark.trio
async def test_status_storage(
    fa_client_async: AsyncClient, device_setup: DeviceSetup, tmp_path
) -> None:
    dev, camera, _ = device_setup
    device_id = dev.id

    assert not dev.persist.device_dir_path

    response = await fa_client_async.get(f"/devices/{device_id}/configuration")
    payload = response.json()
    assert payload["status"][StatusType.STORAGE_USAGE]["value"] == 0

    # To update StorageSizeWatcher
    dev.persist.device_dir_path = tmp_path
    camera.update_storage_config(dev.persist)

    # For image_dir_for and inference_dir_for
    Config().update_persistent_attr(device_id, "device_dir_path", tmp_path)

    file_a = image_dir_for(device_id) / "a"
    file_a_content = b"a few bytes"
    file_a.write_bytes(file_a_content)

    response = await fa_client_async.get(f"/devices/{device_id}/configuration")
    payload = response.json()
    assert payload["status"][StatusType.STORAGE_USAGE]["value"] == len(file_a_content)

    file_b = inference_dir_for(device_id) / "b"
    file_b_content = b"a few more bytes"
    file_b.write_bytes(file_b_content)

    other_path = base_dir_for(device_id) / "Other folder"
    other_path.mkdir()
    file_c = other_path / "c"
    file_c_content = b"a few more bytes"
    file_c.write_bytes(file_c_content)

    response = await fa_client_async.get(f"/devices/{device_id}/configuration")
    payload = response.json()
    assert payload["status"][StatusType.STORAGE_USAGE]["value"] == len(
        file_a_content
    ) + len(file_b_content)


@pytest.mark.trio
async def test_patch_configuration_dry_run(
    fa_client_async: AsyncClient, device_setup: DeviceSetup, tmp_path
) -> None:
    dev, _, _ = device_setup

    response = await fa_client_async.get(f"/devices/{dev.id}/configuration")
    original_payload = response.json()

    num_bytes = randint(1, 1000)
    base_path = tmp_path / str(dev.id) / "Images"
    base_path.mkdir(parents=True)
    file = base_path / "myfile"
    file.write_bytes(b"0" * num_bytes)

    # dry-run patch request
    result = await fa_client_async.patch(
        f"/devices/{dev.id}/configuration?dry_run=true",
        json={"device_dir_path": str(tmp_path)},
    )
    # path not set
    assert result.json()["device_dir_path"] is None
    # no folder error
    assert "FOLDER_ERROR" not in result.json()["status"]
    # storage usage is from dry-run `device_dir_path`
    assert result.json()["status"]["STORAGE_USAGE"]["value"] == num_bytes

    # configuration is not modified
    response = await fa_client_async.get(f"/devices/{dev.id}/configuration")
    payload = response.json()
    assert original_payload == payload


@pytest.mark.trio
async def test_patch_configuration_dry_run_error(
    fa_client_async: AsyncClient, device_setup: DeviceSetup, tmp_path
) -> None:
    dev, _, _ = device_setup

    response = await fa_client_async.get(
        f"/devices/{dev.id}/configuration?dry_run=true"
    )
    original_payload = response.json()

    with (patch("pathlib.Path.write_text", side_effect=IOError("could not write")),):
        result = await fa_client_async.patch(
            f"/devices/{dev.id}/configuration",
            json={"device_dir_path": str(tmp_path)},
        )
        assert result.json()["device_dir_path"] == original_payload["device_dir_path"]
        # folder error
        assert "FOLDER_ERROR" in result.json()["status"]
        # storage usage is 0, as there is a folder error
        assert result.json()["status"]["STORAGE_USAGE"]["value"] == 0

    # configuration is not modified
    response = await fa_client_async.get(f"/devices/{dev.id}/configuration")
    payload = response.json()
    assert original_payload == payload
