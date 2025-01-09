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
from local_console.core.edge_apps import EdgeAppsManager
from local_console.fastapi.routes.edge_apps import EdgeAppInfoDTO
from local_console.fastapi.routes.edge_apps import GetEdgeAppsRequestOutDTO
from starlette.testclient import TestClient

from tests.fixtures.fastapi import fa_client
from tests.mocks.files import MockedFileManager


def test_edge_apps_post_success(fa_client: TestClient):
    edge_apps_manager = EdgeAppsManager(MockedFileManager())
    fa_client.app.state.edge_apps_manager = edge_apps_manager

    payload = {
        "app_name": "edge_app_name_1",
        "edge_app_package_id": "edge_app_package_id_1",
    }

    response_post = fa_client.post("/edge_apps", json=payload)

    assert response_post.status_code == 200
    assert response_post.json() == {"result": "SUCCESS"}

    response_get = fa_client.get("/edge_apps")

    assert GetEdgeAppsRequestOutDTO(**response_get.json()) == GetEdgeAppsRequestOutDTO(
        apps=[EdgeAppInfoDTO(app_name="edge_app_name_1", versions=[])],
        continuation_token=None,
    )
    assert edge_apps_manager.get_by_id("edge_app_package_id_1") is not None


def test_get_edge_apps_empty(fa_client: TestClient) -> None:
    edge_apps_manager = EdgeAppsManager(MockedFileManager())
    fa_client.app.state.edge_apps_manager = edge_apps_manager

    response = fa_client.get("/edge_apps")

    assert response.status_code == 200
    assert response.json() == {"apps": [], "continuation_token": None}


def test_post_edge_apps_missing_fields(fa_client: TestClient) -> None:
    edge_apps_manager = EdgeAppsManager(MockedFileManager())
    fa_client.app.state.edge_apps_manager = edge_apps_manager

    # Missing 'app_name'
    response = fa_client.post("/edge_apps", json={"app_name": "edge_app_name_1"})

    assert response.status_code == 422
    assert response.json()["message"] == "edge_app_package_id: Field required"


def test_post_edge_apps_duplicate_model_id(fa_client: TestClient) -> None:
    edge_apps_manager = EdgeAppsManager(MockedFileManager())
    fa_client.app.state.edge_apps_manager = edge_apps_manager

    payload = {
        "app_name": "edge_app_name_1",
        "edge_app_package_id": "edge_app_package_id_1",
    }
    fa_client.post("/edge_apps", json=payload)
    # Duplicate registration
    response_post = fa_client.post("/edge_apps", json=payload)

    assert response_post.status_code == 200
    assert response_post.json() == {"result": "SUCCESS"}

    response_get = fa_client.get("/edge_apps")

    # Ensure it is registered only once
    assert len(GetEdgeAppsRequestOutDTO(**response_get.json()).apps) == 1
    assert edge_apps_manager.get_by_id("edge_app_package_id_1") is not None


def test_post_edge_apps_invalid_json(fa_client: TestClient) -> None:
    edge_apps_manager = EdgeAppsManager(MockedFileManager())
    fa_client.app.state.edge_apps_manager = edge_apps_manager
    payload = "Invalid JSON string"

    response = fa_client.post(
        "/edge_apps", data=payload, headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422
    assert response.json()["message"] == "0: JSON decode error"


def test_edge_apps_post_missing_file(fa_client: TestClient):
    file_manager = MockedFileManager()
    file_manager.mocked_filed = None
    edge_apps_manager = EdgeAppsManager(file_manager)

    fa_client.app.state.edge_apps_manager = edge_apps_manager

    file_id = "app_id_1"

    response = fa_client.post(
        "/edge_apps",
        json={
            "app_name": "app_name_1",
            "edge_app_package_id": file_id,
        },
    )
    assert response.status_code == 404

    assert response.json()["message"] == f"Could not find file {file_id}"


def test_edge_apps_get_limit(fa_client: TestClient):
    fa_client.app.state.edge_apps_manager = EdgeAppsManager(MockedFileManager())

    payload_1 = {
        "app_name": "edge_app_name_1",
        "edge_app_package_id": "file_id_1",
    }

    payload_2 = {
        "app_name": "edge_app_name_2",
        "edge_app_package_id": "file_id_2",
    }

    response_post = fa_client.post("/edge_apps", json=payload_1)
    assert response_post.status_code == 200
    response_post = fa_client.post("/edge_apps", json=payload_2)
    assert response_post.status_code == 200

    # Make sure both apps have been properly registered
    response_get = fa_client.get("/edge_apps")
    assert len(GetEdgeAppsRequestOutDTO(**response_get.json()).apps) == 2

    # Make sure we are getting only a single app
    response_get = fa_client.get("/edge_apps?limit=1")
    assert len(GetEdgeAppsRequestOutDTO(**response_get.json()).apps) == 1

    assert response_get.json()["continuation_token"] == "file_id_1"


def test_edge_apps_get_continuation_token(fa_client: TestClient):
    fa_client.app.state.edge_apps_manager = EdgeAppsManager(MockedFileManager())

    payload_1 = {
        "app_name": "edge_app_name_1",
        "edge_app_package_id": "file_id_1",
    }

    payload_2 = {
        "app_name": "edge_app_name_2",
        "edge_app_package_id": "file_id_2",
    }

    response_post = fa_client.post("/edge_apps", json=payload_1)
    assert response_post.status_code == 200
    response_post = fa_client.post("/edge_apps", json=payload_2)
    assert response_post.status_code == 200

    # Make sure both apps have been properly registered
    response_get = fa_client.get("/edge_apps")
    assert len(GetEdgeAppsRequestOutDTO(**response_get.json()).apps) == 2

    # Make sure we are getting only a single app
    continuation_token = min(
        payload_1["edge_app_package_id"], payload_2["edge_app_package_id"]
    )
    response_get = fa_client.get(f"/edge_apps?starting_after={continuation_token}")
    assert len(GetEdgeAppsRequestOutDTO(**response_get.json()).apps) == 1
