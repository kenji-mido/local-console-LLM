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

from fastapi import status
from fastapi.testclient import TestClient
from local_console.core.camera.state import CameraState
from local_console.fastapi.routes.images.dependencies import device_image_manager

from tests.fixtures.fastapi import fa_client


def test_get_device_images(fa_client: TestClient) -> None:
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        base_path = Path(temporary_dir)
        files = [base_path / "image1.jpg", base_path / "image2.jpg"]
        for file in files:
            file.write_text("content")
        device_id = 1883
        fa_client.app.state.device_service.states[device_id] = CameraState(
            MagicMock(), MagicMock()
        )
        fa_client.app.state.device_service.states[device_id].image_dir_path.value = (
            Path(temporary_dir)
        )

        result = fa_client.get(
            f"/images/devices/{device_id}/directories/subdirectory_is_ignored"
        )

        assert result.status_code == status.HTTP_200_OK
        images = result.json()["data"]
        assert sorted(images, key=lambda e: e["name"]) == sorted(
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


def test_device_is_int(fa_client: TestClient) -> None:
    result = fa_client.get(
        "/images/devices/not_int/directories/subdirectory_is_ignored"
    )

    assert result.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert (
        result.json()["message"]
        == "device_id: Input should be a valid integer, unable to parse string as an integer"
    )


def test_ignore_subdir(fa_client: TestClient) -> None:
    from local_console.fastapi.routes.images.dependencies import device_image_manager

    mock_manager = MagicMock()
    fa_client.app.dependency_overrides[device_image_manager] = lambda: mock_manager
    mock_manager.list_for.return_value = []

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


def test_download_image_not_found(fa_client: TestClient) -> None:
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        device_id = 1883
        fa_client.app.state.device_service.states[device_id] = CameraState(
            MagicMock(), MagicMock()
        )
        fa_client.app.state.device_service.states[device_id].image_dir_path.value = (
            Path(temporary_dir)
        )
        result = fa_client.get(f"/images/devices/{device_id}/image/image1.jpg")

        assert result.status_code == status.HTTP_404_NOT_FOUND
        assert result.json()["message"] == "File 'image1.jpg' does not exist"


def test_image_pagination(fa_client: TestClient) -> None:
    manager = MagicMock()
    fa_client.app.dependency_overrides[device_image_manager] = lambda: manager

    manager.list_for.return_value = [Path(f"image{i+1}.jpg") for i in range(10)]

    result = fa_client.get(
        "/images/devices/1/directories/subdirectory_is_ignored?limit=2"
    )

    assert result.status_code == status.HTTP_200_OK
    images = result.json()["data"]
    assert sorted(images, key=lambda e: e["name"]) == sorted(
        [
            {
                "name": "image1.jpg",
                "sas_url": "/images/devices/1/image/image1.jpg",
            },
            {
                "name": "image2.jpg",
                "sas_url": "/images/devices/1/image/image2.jpg",
            },
        ],
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
