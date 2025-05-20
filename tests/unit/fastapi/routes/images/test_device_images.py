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
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from local_console.core.camera.machine import Camera
from local_console.core.camera.states.v1.streaming import StreamingCameraV1
from local_console.core.camera.streaming import image_dir_for
from local_console.core.config import Config
from local_console.core.schemas.schemas import DeviceConnection
from local_console.core.schemas.schemas import GlobalConfiguration
from local_console.fastapi.routes.images.dependencies import device_image_manager


ImageSetupArgs = [TestClient, int, Camera]


@pytest.fixture
def image_setup(
    fa_client: TestClient,
    single_device_config: GlobalConfiguration,
    tmp_path,
) -> Generator[ImageSetupArgs, None, None]:
    device_id = 1883
    Config().update_persistent_attr(device_id, "device_dir_path", tmp_path)

    image_dir = image_dir_for(device_id)
    image_dir.mkdir(parents=True)
    files = [image_dir / "image1.jpg", image_dir / "image2.jpg"]
    for file in files:
        file.write_text("content")

    config: DeviceConnection = single_device_config.devices[0]
    config.mqtt.port = device_id
    camera = Camera(
        config, MagicMock(), MagicMock(), MagicMock(), MagicMock(), lambda *args: None
    )
    camera._state = StreamingCameraV1(camera._common_properties, {}, {})

    fa_client.app.state.device_service.set_camera(device_id, camera)

    yield fa_client, device_id, camera


@pytest.mark.parametrize(
    "with_preview",
    [
        False,  # default case
        True,  # for preview mode
    ],
)
def test_get_device_images(with_preview: bool, image_setup: ImageSetupArgs) -> None:
    fa_client, device_id, camera = image_setup

    if with_preview:
        # simulate some preview data has arrived
        camera._state._preview.enable()
        camera._state._preview.update(b"content")

    result = fa_client.get(f"/images/devices/{device_id}/directories")

    assert result.status_code == status.HTTP_200_OK
    images = result.json()["data"]

    if with_preview:
        assert images[0]["sas_url"].endswith("/preview")
    else:
        assert not images[0]["sas_url"].endswith("/preview")

    # The array slice below avoids
    # the preview image, when enabled.
    assert images[-2:] == sorted(
        [
            {
                "name": "image1.jpg",
                "sas_url": f"/images/devices/{device_id}/image/image1.jpg",
            },
            {
                "name": "image2.jpg",
                "sas_url": f"/images/devices/{device_id}/image/image2.jpg",
            },
        ],
        key=lambda e: e["name"],
        reverse=True,
    )

    for img in images:
        result = fa_client.get(img["sas_url"])
        assert result.status_code == status.HTTP_200_OK
        assert result.content == b"content"
        content_disposition = result.headers.get("Content-Disposition")
        assert content_disposition is not None
        assert "attachment" in content_disposition
        name = img["name"]
        assert f'filename="{name}"' in content_disposition


def test_get_device_preview_not_started(image_setup: ImageSetupArgs) -> None:
    fa_client, device_id, camera = image_setup

    # initial state
    assert not camera._state._preview.active
    assert camera._state._preview.last_updated is None

    # what happens when a new frame comes
    with patch("local_console.core.camera.streaming.now") as mock_now:
        camera._state._preview.update(b"some-leftover-data")
        mock_now.assert_called_once()

    # how to get the image over the API
    result = fa_client.get(f"/images/devices/{device_id}/preview")
    assert result.status_code == status.HTTP_200_OK
    assert result.content == b"some-leftover-data"
    content_disposition = result.headers.get("Content-Disposition")
    assert content_disposition is not None
    assert "attachment" in content_disposition


def test_device_is_int(fa_client: TestClient) -> None:
    result = fa_client.get("/images/devices/not_int/directories")

    assert result.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert (
        result.json()["message"]
        == "device_id: Input should be a valid integer, unable to parse string as an integer"
    )


def test_ignore_subdir(fa_client: TestClient) -> None:
    from local_console.fastapi.routes.images.dependencies import device_image_manager

    mock_manager = MagicMock()
    mock_manager.list_for.return_value = []
    mock_manager.with_preview.return_value = False

    fa_client.app.dependency_overrides[device_image_manager] = lambda: mock_manager
    result = fa_client.get("/images/devices/1/directories")

    assert result.status_code == status.HTTP_200_OK
    assert result.json()["data"] == []
    mock_manager.list_for.assert_called_once_with(1)


def test_download_device_not_int(fa_client: TestClient) -> None:
    result = fa_client.get("/images/devices/not_an_int/image/image1.jpg")

    assert result.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert (
        result.json()["message"]
        == "device_id: Input should be a valid integer, unable to parse string as an integer"
    )


def test_download_device_not_found(fa_client: TestClient) -> None:
    result = fa_client.get("/images/devices/1/image/image1.jpg")

    assert result.status_code == status.HTTP_404_NOT_FOUND
    assert result.json()["message"] == "Device for port 1 not found"


def test_download_image_not_found(image_setup: ImageSetupArgs) -> None:
    fa_client, device_id, camera_state = image_setup
    result = fa_client.get(f"/images/devices/{device_id}/image/image999.jpg")

    assert result.status_code == status.HTTP_404_NOT_FOUND
    assert result.json()["message"] == "File 'image999.jpg' does not exist"


@pytest.mark.parametrize(
    "with_preview",
    [
        False,  # default case
        True,  # for preview mode
    ],
)
@patch(
    "local_console.fastapi.routes.images.controller.as_timestamp",
    return_value="image10",
)
def test_image_pagination(mock_ts, with_preview: bool, fa_client: TestClient) -> None:
    manager = MagicMock()
    manager.with_preview.return_value = with_preview
    manager.list_for.return_value = [Path(f"image{i+1}.jpg") for i in range(10)]

    fa_client.app.dependency_overrides[device_image_manager] = lambda: manager
    result = fa_client.get("/images/devices/1/directories?limit=2")
    expected = [
        {
            "name": "image1.jpg",
            "sas_url": "/images/devices/1/image/image1.jpg",
        },
        {
            "name": "image2.jpg",
            "sas_url": "/images/devices/1/image/image2.jpg",
        },
    ]
    if with_preview:
        expected.append(
            {
                "name": "image10.jpg",
                "sas_url": "/images/devices/1/preview",
            }
        )

    assert result.status_code == status.HTTP_200_OK
    images = result.json()["data"]
    assert sorted(images, key=lambda e: e["name"]) == sorted(
        expected,
        key=lambda e: e["name"],
    )
    assert result.json()["continuation_token"] == "image2.jpg"

    result = fa_client.get(
        "/images/devices/1/directories?limit=2&starting_after=image2.jpg"
    )

    assert result.status_code == status.HTTP_200_OK
    images = result.json()["data"]
    assert sorted(images, key=lambda e: e["name"]) == sorted(
        [
            {
                "name": "image3.jpg",
                "sas_url": "/images/devices/1/image/image3.jpg",
            },
            {
                "name": "image4.jpg",
                "sas_url": "/images/devices/1/image/image4.jpg",
            },
        ],
        key=lambda e: e["name"],
    )
    assert result.json()["continuation_token"] == "image4.jpg"
