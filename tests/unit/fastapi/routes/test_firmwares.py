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
from local_console.fastapi.dependencies.deploy import firmware_manager
from starlette.testclient import TestClient

from tests.fixtures.fastapi import fa_client
from tests.strategies.samplers.files import FileInfoSampler


def test_get_firmware(fa_client: TestClient) -> None:
    fa_client.app.state.file_manager.get_file.side_effect = [
        FileInfoSampler(id="file_id_1").sample(),
        FileInfoSampler(id="file_id_2").sample(),
    ]
    fa_client.app.state.file_manager.get_file.return_value = FileInfoSampler().sample()

    fa_client.post(
        "/firmwares",
        json={
            "firmware_type": "SensorFw",
            "description": "description_1",
            "file_id": "file_id_1",
            "version": "v0.1",
        },
    )
    fa_client.post(
        "/firmwares",
        json={
            "firmware_type": "DnnModel",
            "description": "description_2",
            "file_id": "file_id_2",
            "version": "v0.2",
        },
    )

    response = fa_client.get("/firmwares")

    assert response.status_code == 200
    json_response = response.json()

    expected_firmwares = [
        {
            "firmware_id": "file_id_1",
            "firmware_type": "SensorFw",
            "firmware_version": "v0.1",
            "description": "description_1",
            "ins_date": None,
            "ins_id": None,
            "manifest": None,
            "target_device_types": None,
            "upd_date": None,
            "upd_id": None,
        },
        {
            "firmware_id": "file_id_2",
            "firmware_type": "DnnModel",
            "firmware_version": "v0.2",
            "description": "description_2",
            "ins_date": None,
            "ins_id": None,
            "manifest": None,
            "target_device_types": None,
            "upd_date": None,
            "upd_id": None,
        },
    ]

    assert json_response["continuation_token"] is None
    assert json_response["firmwares"] == expected_firmwares


def test_get_firmwares_limit(fa_client: TestClient) -> None:
    fa_client.app.state.file_manager.get_file.side_effect = [
        FileInfoSampler(id="file_id_1").sample(),
        FileInfoSampler(id="file_id_2").sample(),
    ]
    fa_client.app.state.file_manager.get_file.return_value = FileInfoSampler().sample()

    fa_client.post(
        "/firmwares",
        json={
            "firmware_type": "SensorFw",
            "description": "description_1",
            "file_id": "file_id_1",
            "version": "v0.1",
        },
    )
    fa_client.post(
        "/firmwares",
        json={
            "firmware_type": "DnnModel",
            "description": "description_2",
            "file_id": "file_id_2",
            "version": "v0.2",
        },
    )

    response = fa_client.get("/firmwares?limit=1")

    assert response.status_code == 200
    json_response = response.json()

    expected_firmwares = [
        {
            "firmware_id": "file_id_1",
            "firmware_type": "SensorFw",
            "firmware_version": "v0.1",
            "description": "description_1",
            "ins_date": None,
            "ins_id": None,
            "manifest": None,
            "target_device_types": None,
            "upd_date": None,
            "upd_id": None,
        }
    ]

    assert json_response["continuation_token"] == "file_id_1"
    assert json_response["firmwares"] == expected_firmwares


def test_get_firmwares_continuation_token_ending(fa_client: TestClient) -> None:
    fa_client.app.state.file_manager.get_file.side_effect = [
        FileInfoSampler(id="file_id_1").sample(),
        FileInfoSampler(id="file_id_2").sample(),
    ]
    fa_client.app.state.file_manager.get_file.return_value = FileInfoSampler().sample()

    fa_client.post(
        "/firmwares",
        json={
            "firmware_type": "SensorFw",
            "description": "description_1",
            "file_id": "file_id_1",
            "version": "v0.1",
        },
    )
    fa_client.post(
        "/firmwares",
        json={
            "firmware_type": "DnnModel",
            "description": "description_2",
            "file_id": "file_id_2",
            "version": "v0.2",
        },
    )

    response = fa_client.get("/firmwares?starting_after=file_id_1")

    assert response.status_code == 200
    json_response = response.json()

    expected_firmwares = [
        {
            "firmware_id": "file_id_2",
            "firmware_type": "DnnModel",
            "firmware_version": "v0.2",
            "description": "description_2",
            "ins_date": None,
            "ins_id": None,
            "manifest": None,
            "target_device_types": None,
            "upd_date": None,
            "upd_id": None,
        }
    ]

    assert json_response["continuation_token"] is None
    assert json_response["firmwares"] == expected_firmwares


def test_get_firmwares_continuation_token_limit(fa_client: TestClient) -> None:
    fa_client.app.state.file_manager.get_file.side_effect = [
        FileInfoSampler(id="file_id_1").sample(),
        FileInfoSampler(id="file_id_2").sample(),
        FileInfoSampler(id="file_id_3").sample(),
    ]
    fa_client.app.state.file_manager.get_file.return_value = FileInfoSampler().sample()

    fa_client.post(
        "/firmwares",
        json={
            "firmware_type": "SensorFw",
            "description": "description_1",
            "file_id": "file_id_1",
            "version": "v0.1",
        },
    )
    fa_client.post(
        "/firmwares",
        json={
            "firmware_type": "DnnModel",
            "description": "description_2",
            "file_id": "file_id_2",
            "version": "v0.2",
        },
    )
    fa_client.post(
        "/firmwares",
        json={
            "firmware_type": "DnnModel",
            "description": "description_3",
            "file_id": "file_id_3",
            "version": "v0.3",
        },
    )

    response = fa_client.get("/firmwares?starting_after=file_id_1&limit=1")

    assert response.status_code == 200
    json_response = response.json()

    expected_firmwares = [
        {
            "firmware_id": "file_id_2",
            "firmware_type": "DnnModel",
            "firmware_version": "v0.2",
            "description": "description_2",
            "ins_date": None,
            "ins_id": None,
            "manifest": None,
            "target_device_types": None,
            "upd_date": None,
            "upd_id": None,
        }
    ]

    assert json_response["continuation_token"] == "file_id_2"
    assert json_response["firmwares"] == expected_firmwares


def test_post_firmware(fa_client: TestClient) -> None:
    fa_client.app.state.file_manager.get_file.return_value = FileInfoSampler().sample()
    response = fa_client.post(
        "/firmwares",
        json={
            "firmware_type": "SensorFw",
            "description": "",
            "file_id": "file_42",
            "version": "v0.1",
        },
    )
    assert response.status_code == 200

    assert response.json()["result"] == "SUCCESS"


def test_post_firmware_not_found(fa_client: TestClient) -> None:
    fa_client.app.state.file_manager.get_file.return_value = None
    file_id = "file_42"

    response = fa_client.post(
        "/firmwares",
        json={
            "firmware_type": "DnnModel",
            "description": "",
            "file_id": file_id,
            "version": "v0.1",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "result": "ERROR",
        "message": f"Could not find file {file_id}",
        "code": "101001",
    }


def test_singleton_firmware_manager(fa_client: TestClient):
    fm_1 = firmware_manager(fa_client)
    fm_2 = firmware_manager(fa_client)

    assert fm_1 == fm_2
