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
from unittest.mock import MagicMock

from local_console.core.deploy_config import DeployConfig
from local_console.fastapi.dependencies.deploy import deploy_config_manager
from starlette.testclient import TestClient

from tests.strategies.samplers.files import FileInfoSampler
from tests.strategies.samplers.files import FirmwareSampler


def test_post_deploy_configs_model_not_found(fa_client: TestClient) -> None:
    response = fa_client.post(
        "/deploy_configs",
        json={
            "config_id": "id",
            "description": "hello",
            "models": [{"model_id": "model_id", "model_version_number": "latest"}],
            "edge_apps": [],
        },
    )
    assert response.status_code == 404

    assert response.json()["result"] == "ERROR"
    assert (
        response.json()["message"]
        == "Could not find file Model id model_id not registered"
    )


def test_post_deploy_configs_edge_app_not_found(fa_client: TestClient) -> None:

    fa_client.app.state.file_manager.get_file.return_value = None

    response = fa_client.post(
        "/deploy_configs",
        json={
            "config_id": "id",
            "description": "hello",
            "models": [],
            "edge_apps": [
                {
                    "edge_app_package_id": "app_id",
                    "app_name": "name",
                    "app_version": "version",
                }
            ],
        },
    )
    assert response.status_code == 404

    assert response.json()["result"] == "ERROR"
    assert (
        response.json()["message"]
        == "Could not find file Edge app id app_id not registered"
    )


def test_post_deploy_configs_fw_not_found(fa_client: TestClient) -> None:

    fa_client.app.state.file_manager.get_file.return_value = None

    response = fa_client.post(
        "/deploy_configs",
        json={
            "config_id": "id",
            "description": "hello",
            "models": [],
            "edge_system_sw_package": {"firmware_id": "sadh"},
            "edge_apps": [],
        },
    )
    assert response.status_code == 404

    assert response.json()["result"] == "ERROR"
    assert (
        response.json()["message"]
        == "Could not find file Firmware id sadh not registered"
    )


def test_post_deploy_configs_success(fa_client: TestClient) -> None:
    fa_client.app.state.file_manager.get_file.return_value = FileInfoSampler().sample()

    fa_client.post("/models", json={"model_id": "model_id", "model_file_id": "file_1"})
    fa_client.post(
        "/edge_apps",
        json={
            "app_name": "edge_app_name_1",
            "edge_app_package_id": "edge_app_package_id_1",
        },
    )
    fa_client.post(
        "/firmwares",
        json={
            "firmware_type": "SensorFw",
            "description": "",
            "file_id": "fw_id",
            "version": "v0.1",
        },
    )

    response = fa_client.post(
        "/deploy_configs",
        json={
            "config_id": "mock_id",
            "description": "description",
            "models": [{"model_id": "model_id", "model_version_number": "latest"}],
            "edge_system_sw_package": {"firmware_id": "fw_id"},
            "edge_apps": [
                {
                    "edge_app_package_id": "edge_app_package_id_1",
                    "app_name": "name",
                    "app_version": "version",
                }
            ],
        },
    )
    assert response.status_code == 200

    assert response.json()["result"] == "SUCCESS"


def test_post_deploy_still_accepst_single_and_multiple_firmware(
    fa_client: TestClient,
) -> None:
    firmware1 = FirmwareSampler(firmware_id="1").sample()
    fw_manager = MagicMock()
    fa_client.app.state.deploy_config_manager._fw_manager = fw_manager
    fw_manager.get_by_id.return_value = firmware1
    response = fa_client.post(
        "/deploy_configs",
        json={
            "config_id": "config_1",
            "description": "description",
            "models": [],
            "edge_system_sw_package": {"firmware_id": "ignored_but_represents_1"},
            "edge_apps": [],
        },
    )

    assert response.status_code == 200
    config: DeployConfig | None = fa_client.app.state.deploy_config_manager.get_by_id(
        "config_1"
    )
    assert config
    assert config.firmwares[0].firmware_id == "1"

    firmware2 = FirmwareSampler(firmware_id="2").sample()
    fw_manager.get_by_id.return_value = firmware2
    response = fa_client.post(
        "/deploy_configs",
        json={
            "config_id": "config_2",
            "description": "description",
            "models": [],
            "edge_system_sw_package": [{"firmware_id": "ignored_but_represents_2"}],
            "edge_apps": [],
        },
    )

    assert response.status_code == 200
    config: DeployConfig | None = fa_client.app.state.deploy_config_manager.get_by_id(
        "config_2"
    )
    assert config
    assert config.firmwares[0].firmware_id == "2"


def test_singleton_deploy_manager(fa_client: TestClient):
    fm_1 = deploy_config_manager(fa_client)
    fm_2 = deploy_config_manager(fa_client)

    assert fm_1 == fm_2
