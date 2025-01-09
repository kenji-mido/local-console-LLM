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
from unittest.mock import call

from fastapi.testclient import TestClient
from local_console.core.files.values import FileType
from local_console.fastapi.routes.models import GetModelsOutDTO
from local_console.fastapi.routes.models import ModelDTO

from tests.fixtures.fastapi import fa_client
from tests.strategies.samplers.files import FileInfoSampler


def test_post_models_success(fa_client: TestClient) -> None:
    payload = {"model_id": "model_1", "model_file_id": "file_1"}
    fa_client.app.state.file_manager.get_file.return_value = FileInfoSampler().sample()
    response = fa_client.post("/models", json=payload)

    assert response.status_code == 200
    assert response.json() == {"result": "SUCCESS"}
    response = fa_client.get("/models")
    assert GetModelsOutDTO(**response.json()) == GetModelsOutDTO(
        models=[ModelDTO(model_id="model_1")], continuation_token=None
    )
    assert fa_client.app.state.model_manager.get_by_id("model_1") is not None
    fa_client.app.state.file_manager.get_file.assert_called_with(
        FileType.MODEL, "file_1"
    )


def test_post_file_not_found(fa_client: TestClient) -> None:
    fa_client.app.state.file_manager.get_file.return_value = None
    payload = {"model_id": "model_1", "model_file_id": "file_1"}

    response = fa_client.post("/models", json=payload)

    assert response.status_code == 404
    assert response.json() == {
        "result": "ERROR",
        "message": "Could not find file file_1",
        "code": "101001",
    }
    assert fa_client.app.state.model_manager.get_by_id("model_1") is None
    fa_client.app.state.file_manager.get_file.assert_called_with(
        FileType.MODEL, "file_1"
    )


def test_get_models_empty(fa_client: TestClient) -> None:
    response = fa_client.get("/models")

    assert response.status_code == 200
    assert response.json() == {"models": [], "continuation_token": None}


def test_get_models_after_post(fa_client: TestClient) -> None:
    fa_client.app.state.file_manager.get_file.return_value = FileInfoSampler().sample()

    fa_client.post("/models", json={"model_id": "model_1", "model_file_id": "file_1"})
    response = fa_client.get("/models")

    assert response.status_code == 200
    assert response.json() == {
        "models": [{"model_id": "model_1"}],
        "continuation_token": None,
    }


def test_post_models_missing_fields(fa_client: TestClient) -> None:
    # Missing 'model_file_id'
    response = fa_client.post("/models", json={"model_id": "model_1"})

    assert response.status_code == 422
    assert response.json()["message"] == "model_file_id: Field required"
    fa_client.app.state.file_manager.get_file.assert_not_called()


def test_post_models_invalid_model_id(fa_client: TestClient) -> None:
    # model_id exceeds max_length
    response = fa_client.post(
        "/models",
        json={
            "model_id": "a" * 101,
            "model_file_id": "file_1",
        },
    )

    assert response.status_code == 422
    assert (
        "model_id: String should have at most 100 characters"
        == response.json()["message"]
    )
    fa_client.app.state.file_manager.get_file.assert_not_called()


def test_post_models_duplicate_model_id(fa_client: TestClient) -> None:
    fa_client.app.state.file_manager.get_file.return_value = FileInfoSampler().sample()
    payload = {"model_id": "model_1", "model_file_id": "file_1"}
    fa_client.post("/models", json=payload)
    # Duplicate registration
    response = fa_client.post("/models", json=payload)

    assert response.status_code == 200
    assert response.json() == {"result": "SUCCESS"}
    fa_client.app.state.file_manager.get_file.assert_has_calls(
        [call(FileType.MODEL, "file_1"), call(FileType.MODEL, "file_1")]
    )


def test_post_models_invalid_json(fa_client: TestClient) -> None:
    payload = "Invalid JSON string"

    response = fa_client.post(
        "/models", data=payload, headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422
    assert response.json()["message"] == "0: JSON decode error"
    fa_client.app.state.file_manager.get_file.assert_not_called()


def test_get_models_pagination(fa_client: TestClient) -> None:
    # Register 10 models
    for i in range(10):
        payload = {"model_id": f"model_{i}", "model_file_id": f"file_{i}"}
        fa_client.app.state.file_manager.get_file.return_value = FileInfoSampler(
            id=f"file_{i}"
        ).sample()
        fa_client.post("/models", json=payload)

    # Get first page with limit=3
    response = fa_client.get("/models?limit=3")
    assert response.status_code == 200
    data = response.json()

    expected_models = [{"model_id": f"model_{i}"} for i in range(3)]
    assert data["models"] == expected_models
    assert data["continuation_token"] == "model_2"

    # Get next page using continuation_token
    continuation_token = data["continuation_token"]
    response = fa_client.get(f"/models?limit=3&starting_after={continuation_token}")
    assert response.status_code == 200
    data = response.json()

    expected_models = [{"model_id": f"model_{i}"} for i in range(3, 6)]
    assert data["models"] == expected_models
    assert data["continuation_token"] == "model_5"

    # Get next page
    continuation_token = data["continuation_token"]
    response = fa_client.get(f"/models?limit=3&starting_after={continuation_token}")
    assert response.status_code == 200
    data = response.json()

    expected_models = [{"model_id": f"model_{i}"} for i in range(6, 9)]
    assert data["models"] == expected_models
    assert data["continuation_token"] == "model_8"

    # Get last page
    continuation_token = data["continuation_token"]
    response = fa_client.get(f"/models?limit=3&starting_after={continuation_token}")
    assert response.status_code == 200
    data = response.json()

    # There is only one model left
    expected_models = [{"model_id": "model_9"}]
    assert data["models"] == expected_models
    assert data["continuation_token"] is None


def test_get_models_with_starting_after_not_found(fa_client: TestClient) -> None:
    for i in range(5):
        payload = {"model_id": f"model_{i}", "model_file_id": f"file_{i}"}
        fa_client.app.state.file_manager.get_file.return_value = FileInfoSampler(
            id=f"file_{i}"
        ).sample()
        fa_client.post("/models", json=payload)

    response = fa_client.get("/models?starting_after=nonexistent_model")
    assert response.status_code == 200
    data = response.json()

    # Should return from the beginning
    expected_models = [{"model_id": f"model_{i}"} for i in range(5)]
    assert data["models"] == expected_models
    assert data["continuation_token"] is None


def test_get_models_limit_exceeds_total(fa_client: TestClient) -> None:
    for i in range(2):
        payload = {"model_id": f"model_{i}", "model_file_id": f"file_{i}"}
        fa_client.app.state.file_manager.get_file.return_value = FileInfoSampler(
            id=f"file_{i}"
        ).sample()
        fa_client.post("/models", json=payload)

    response = fa_client.get("/models?limit=10")
    assert response.status_code == 200
    data = response.json()

    # Should return all models
    expected_models = [{"model_id": "model_0"}, {"model_id": "model_1"}]
    assert data["models"] == expected_models
    assert data["continuation_token"] is None


def test_get_models_invalid_limit(fa_client: TestClient) -> None:
    # Exceeds max limit of 256
    response = fa_client.get("/models?limit=300")

    assert response.status_code == 422
    assert (
        "limit: Input should be less than or equal to 256" == response.json()["message"]
    )


def test_get_models_negative_limit(fa_client: TestClient) -> None:
    response = fa_client.get("/models?limit=-1")

    assert response.status_code == 422
    assert (
        "limit: Input should be greater than or equal to 0"
        == response.json()["message"]
    )
