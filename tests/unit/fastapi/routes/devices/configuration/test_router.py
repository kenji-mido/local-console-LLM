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
from typing import Any
from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from local_console.core.camera.enums import ApplicationType
from local_console.core.camera.enums import UnitScale
from local_console.core.camera.state import CameraState
from local_console.core.device_services import DeviceConnection
from local_console.core.enums import ApplicationSchemaFilePath
from local_console.fastapi.routes.devices.configuration.dto import (
    CameraConfigurationDTO,
)

from tests.fixtures.configs import stored_devices
from tests.fixtures.fastapi import fa_client
from tests.strategies.samplers.configs import DeviceConnectionSampler


def _device_setup(
    fa_client: TestClient,
) -> Generator[tuple[DeviceConnection, CameraState], None, None]:
    expected_devices = DeviceConnectionSampler().list_of_samples(1)
    dev_svc = fa_client.app.state.device_service
    with stored_devices(expected_devices, dev_svc):
        dev = expected_devices[0]
        dev_state = next(iter(dev_svc.states.values()))
        yield dev, dev_state


@pytest.fixture
def device_setup(
    fa_client: TestClient,
) -> Generator[tuple[DeviceConnection, CameraState], None, None]:
    """
    Used to avoid side-effects when updating the variables such as PermissionsError for artificial paths.
    """
    with patch("local_console.core.camera.state.CameraState._init_bindings"):
        yield from _device_setup(fa_client)


@pytest.fixture
def device_setup_without_mock_bindings(
    fa_client: TestClient,
) -> Generator[tuple[DeviceConnection, CameraState], None, None]:
    yield from _device_setup(fa_client)


def test_get_configuration_exists_with_default_values(
    fa_client: TestClient, device_setup: tuple[DeviceConnection, CameraState]
) -> None:

    dev, _ = device_setup
    response = fa_client.get(f"/devices/{dev.mqtt.port}/configuration")
    assert response.status_code == 200

    payload = response.json()
    assert set(CameraConfigurationDTO.model_fields.keys()) == set(payload.keys())

    assert payload["image_dir_path"] is None
    assert payload["inference_dir_path"] is None
    assert payload["size"] == 100
    assert payload["unit"] == "MB"
    assert payload["vapp_type"] is None
    assert payload["vapp_config_file"] is None
    assert payload["vapp_labels_file"] is None


def test_get_configuration_exists_with_some_values(
    fa_client: TestClient, device_setup: tuple[DeviceConnection, CameraState]
) -> None:
    dev, dev_state = device_setup
    dev_state.image_dir_path.value = "/tmp/images"
    dev_state.inference_dir_path.value = "/tmp/inferences"
    dev_state.size.value = 5
    dev_state.unit.value = UnitScale.KB
    dev_state.vapp_type.value = ApplicationType.DETECTION
    dev_state.vapp_config_file.value = "/app/data/config"
    dev_state.vapp_labels_file.value = "/app/data/labels"

    response = fa_client.get(f"/devices/{dev.mqtt.port}/configuration")
    assert response.status_code == 200

    payload = response.json()
    assert set(CameraConfigurationDTO.model_fields.keys()) == set(payload.keys())

    assert payload["image_dir_path"] == "/tmp/images"
    assert payload["inference_dir_path"] == "/tmp/inferences"
    assert payload["size"] == 5
    assert payload["unit"] == "KB"
    assert payload["vapp_type"] == "detection"
    assert payload["vapp_config_file"] == "/app/data/config"
    assert payload["vapp_labels_file"] == "/app/data/labels"


def test_get_configuration_invalid_unit_value(
    fa_client: TestClient, device_setup: tuple[DeviceConnection, CameraState]
) -> None:
    dev, dev_state = device_setup
    dev_state.unit.value = "EiB"

    response = fa_client.get(f"/devices/{dev.mqtt.port}/configuration")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_configuration_invalid_vapp_type(
    fa_client: TestClient, device_setup: tuple[DeviceConnection, CameraState]
) -> None:
    dev, dev_state = device_setup
    dev_state.vapp_type.value = "kernel-driver"

    response = fa_client.get(f"/devices/{dev.mqtt.port}/configuration")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_configuration_does_not_exist(fa_client: TestClient) -> None:

    expected_devices = DeviceConnectionSampler().list_of_samples(1)
    with stored_devices(expected_devices, fa_client.app.state.device_service):

        response = fa_client.get("/devices/0000/configuration")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        payload = response.json()
        assert payload["message"] == "Could not find device 0"


def test_update_happy_path(
    fa_client: TestClient, device_setup: tuple[DeviceConnection, CameraState]
) -> None:
    dev, dev_state = device_setup

    result = fa_client.patch(
        f"/devices/{dev.mqtt.port}/configuration",
        json={
            "image_dir_path": "/path/to/images",
            "inference_dir_path": "/path/to/inferences",
            "size": 6,
            "unit": "KB",
            "vapp_type": "detection",
            "vapp_config_file": "/vapp/config",
            "vapp_labels_file": "/vapp/labels",
        },
    )

    assert result.status_code == 200
    assert dev_state.image_dir_path.value == "/path/to/images"
    assert dev_state.inference_dir_path.value == "/path/to/inferences"
    assert dev_state.size.value == 6
    assert dev_state.unit.value == UnitScale.KB
    assert dev_state.vapp_type.value == ApplicationType.DETECTION
    assert dev_state.vapp_schema_file.value == ApplicationSchemaFilePath.DETECTION
    assert dev_state.vapp_config_file.value == "/vapp/config"
    assert dev_state.vapp_labels_file.value == "/vapp/labels"


@pytest.mark.parametrize(
    "parameter, value, expected_value",
    [
        ("image_dir_path", "/path/to/images", "/path/to/images"),
        ("inference_dir_path", "/path/to/inferences", "/path/to/inferences"),
        ("unit", "KB", UnitScale.KB),
        ("vapp_type", "detection", ApplicationType.DETECTION),
    ],
)
def test_update_individual_fields(
    fa_client: TestClient,
    device_setup: tuple[DeviceConnection, CameraState],
    parameter: str,
    value: str,
    expected_value: Any,
) -> None:
    dev, dev_state = device_setup

    result = fa_client.patch(
        f"/devices/{dev.mqtt.port}/configuration",
        json={parameter: value},
    )
    assert result.status_code == 200

    actual_value = getattr(dev_state, parameter).value
    assert actual_value == expected_value

    if parameter == "vapp_type":
        expected_schema_file = getattr(
            ApplicationSchemaFilePath, expected_value.upper()
        )
        assert dev_state.vapp_schema_file.value == expected_schema_file


def test_update_wrong_value(
    fa_client: TestClient, device_setup: tuple[DeviceConnection, CameraState]
) -> None:
    dev, dev_state = device_setup

    result = fa_client.patch(
        f"/devices/{dev.mqtt.port}/configuration",
        json={
            "unit": "gigapascals",
        },
    )

    assert result.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "unit" in result.text


def test_update_unit_and_size_field(
    fa_client: TestClient,
    device_setup_without_mock_bindings: tuple[DeviceConnection, CameraState],
) -> None:
    dev, dev_state = device_setup_without_mock_bindings

    assert dev_state.total_dir_watcher._size_limit != 123 * 1024
    result = fa_client.patch(
        f"/devices/{dev.mqtt.port}/configuration",
        json={
            "size": 123,
            "unit": "KB",
        },
    )
    assert result.status_code == status.HTTP_200_OK
    assert dev_state.total_dir_watcher._size_limit == 123 * 1024


def test_update_persists(
    fa_client: TestClient,
    device_setup_without_mock_bindings: tuple[DeviceConnection, CameraState],
) -> None:
    from local_console.core.config import config_obj

    dev, dev_state = device_setup_without_mock_bindings
    dev_persistent = next(
        (
            device
            for device in config_obj.config.devices
            if device.mqtt.port == dev.mqtt.port
        ),
        None,
    )
    assert dev_persistent
    assert dev_persistent.persist.size != 123
    assert dev_persistent.persist.unit != "KB"
    assert dev_persistent.persist.image_dir_path != "image/dir/path"
    assert dev_persistent.persist.inference_dir_path != "inference/dir/path"
    fa_client.patch(
        f"/devices/{dev.mqtt.port}/configuration",
        json={
            "size": 123,
            "unit": "KB",
            "image_dir_path": "image/dir/path",
            "inference_dir_path": "inference/dir/path",
        },
    )
    assert dev_persistent.persist.size == "123"
    assert dev_persistent.persist.unit == "KB"
    assert dev_persistent.persist.image_dir_path == "image/dir/path"
    assert dev_persistent.persist.inference_dir_path == "inference/dir/path"
