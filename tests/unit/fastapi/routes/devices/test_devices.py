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
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from local_console.fastapi.routes.commons import EmptySuccess
from local_console.fastapi.routes.devices.controller import DevicesController
from local_console.fastapi.routes.devices.dependencies import devices_controller
from local_console.fastapi.routes.devices.dto import ConfigurationUpdateInDTO
from local_console.fastapi.routes.devices.dto import DeviceListDTO
from local_console.fastapi.routes.devices.dto import DevicePostDTO
from local_console.fastapi.routes.devices.dto import PropertyInfo
from local_console.fastapi.routes.devices.dto import RPCRequestDTO
from local_console.fastapi.routes.devices.dto import RPCResponseDTO
from local_console.fastapi.routes.devices.router import create_device
from local_console.fastapi.routes.devices.router import delete_device
from local_console.fastapi.routes.devices.router import device_rpc
from local_console.fastapi.routes.devices.router import get_devices

from tests.fixtures.configs import stored_devices
from tests.fixtures.fastapi import fa_client
from tests.strategies.samplers.configs import DeviceConnectionSampler


@pytest.mark.trio
async def test_list_calls_controller() -> None:
    devices_controller = MagicMock()
    expected = DeviceListDTO(devices=[])
    length: int = 1
    continuation_token = "next_id"

    devices_controller.list_devices.return_value = expected

    result = await get_devices(
        limit=length,
        continuation_token=continuation_token,
        controller=devices_controller,
    )

    devices_controller.list_devices.assert_called_once_with(length, continuation_token)
    assert result is expected


@pytest.mark.trio
async def test_delete_calls_controller() -> None:
    devices_controller = MagicMock()
    expected = EmptySuccess()
    device_id: int = 1

    devices_controller.delete.return_value = expected

    result = await delete_device(device_id=device_id, controller=devices_controller)

    devices_controller.delete.assert_called_once_with(device_id)
    assert result is expected


@pytest.mark.trio
async def test_rpc_calls_controller() -> None:
    devices_controller = AsyncMock()
    expected = RPCResponseDTO(command_response={"image": "base64Image"})
    request = RPCRequestDTO(
        command_name="direct_get_image",
        parameters={"sensor_name": "IMX500", "crop_h_offset": 0},
    )
    device_id: int = 1

    devices_controller.rpc.return_value = expected

    result = await device_rpc(
        device_id=device_id, rpc_args=request, controller=devices_controller
    )

    devices_controller.rpc.assert_awaited_once_with(device_id, request)
    assert result is expected


@pytest.mark.trio
async def test_create_calls_controller() -> None:
    devices_controller = AsyncMock()
    input = DevicePostDTO(device_name="device", mqtt_port=1883)
    expected = EmptySuccess()

    devices_controller.create.return_value = expected

    result = await create_device(device=input, controller=devices_controller)

    devices_controller.create.assert_called_once_with(input)
    assert result is expected


@patch(
    "local_console.fastapi.routes.devices.controller.lock_until_started", AsyncMock()
)
def test_crud_test(fa_client: TestClient) -> None:
    expected_devices = DeviceConnectionSampler().list_of_samples()
    expected_len = len(expected_devices)
    max_port = max([dev.mqtt.port for dev in expected_devices]) + 1
    with stored_devices(expected_devices, fa_client.app.state.device_service):
        response = fa_client.get("/devices?limit=500")
        assert response.status_code == 200

        assert len(response.json()["devices"]) == expected_len
        for i, expected in enumerate(expected_devices):
            expected = expected_devices[i]
            device = response.json()["devices"][i]
            assert device["device_name"] == expected.name
            assert device["device_id"] == str(expected.mqtt.port)
            assert device["description"] == device["device_name"]
            assert device["internal_device_id"] == device["device_id"]
            assert device["inactivity_timeout"] == 0
            assert device["device_groups"] == []

        response = fa_client.post(
            "/devices",
            json={"device_name": f"new_device_{max_port}", "mqtt_port": max_port},
        )

        assert response.status_code == 200
        assert response.json()["result"] == "SUCCESS"

        response = fa_client.delete(f"/devices/{max_port}")
        assert response.status_code == 200
        assert response.json()["result"] == "SUCCESS"

        response = fa_client.get("/devices?limit=500")
        assert response.status_code == 200

        assert len(response.json()["devices"]) == expected_len


def test_delete_last_device(fa_client: TestClient):
    expected_devices = DeviceConnectionSampler().list_of_samples(1)
    device = expected_devices[0]
    with stored_devices(expected_devices, fa_client.app.state.device_service):
        response = fa_client.delete(f"/devices/{device.mqtt.port}")
        assert response.status_code == status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE
        assert response.json()["result"] == "ERROR"
        assert response.json()["message"] == "You need at least one device to work with"
        assert response.json()["code"] == "120001"


def test_get_image(fa_client: TestClient) -> None:
    mock_controller = AsyncMock(spec=DevicesController)
    fa_client.app.dependency_overrides[devices_controller] = lambda: mock_controller
    image = "test_get_image_result"
    mocked_response = RPCResponseDTO(command_response={"Image": image})
    mock_controller.rpc.return_value = mocked_response
    response = fa_client.post(
        "/devices/1883/modules/$system/command",
        json={
            "command_name": "direct_get_image",
            "parameters": {
                "sensor_name": "IMX500",
                "crop_h_offset": 0,
                "crop_v_offset": 0,
                "crop_h_size": 4056,
                "crop_v_size": 3040,
            },
        },
    )
    mock_controller.rpc.assert_awaited_once()
    assert response.status_code == 200
    rpc_response = response.json()
    assert rpc_response["result"] == "SUCCESS"
    assert rpc_response["command_response"]["Image"] == image


def test_get_image_not_found(fa_client: TestClient) -> None:
    expected_devices = DeviceConnectionSampler().list_of_samples(length=1)
    expected_devices[0].mqtt.port = 1883
    with stored_devices(expected_devices):
        response = fa_client.post(
            "/devices/1884/modules/$system/command",
            json={
                "command_name": "direct_get_image",
                "parameters": {
                    "sensor_name": "IMX500",
                    "crop_h_offset": 0,
                    "crop_v_offset": 0,
                    "crop_h_size": 4056,
                    "crop_v_size": 3040,
                },
            },
        )
        assert response.status_code == 404
        rpc_response = response.json()
        assert rpc_response["result"] == "ERROR"
        assert rpc_response["message"] == "Could not find device 1884"


@patch("local_console.fastapi.routes.devices.controller.DevicesController.configure")
def test_update_module_configuration(mocked_method: AsyncMock, fa_client: TestClient):
    device_id = 42
    module_id = "module_id_1"
    property_name = "property_name_1"
    key = "key_1"
    value = "value_1"
    property = {
        "property": {"configuration": {property_name: {key: value}}},
    }
    ConfigurationUpdateInDTO.model_validate(property)
    response = fa_client.patch(
        f"/devices/{device_id}/modules/{module_id}",
        json=property,
    )

    expected_result = {"result": "SUCCESS", "property": property["property"]}

    assert response.status_code == 200
    assert response.json() == expected_result

    expected_arguments = PropertyInfo.model_validate(
        {"configuration": {property_name: {key: value}}}
    )
    mocked_method.assert_awaited_once_with(
        device_id=device_id, module_id=module_id, property_info=expected_arguments
    )


def test_device_renaming(fa_client: TestClient) -> None:
    expected_devices = DeviceConnectionSampler().list_of_samples(length=1)
    port = expected_devices[0].mqtt.port
    with stored_devices(expected_devices, fa_client.app.state.device_service):
        new_name = "shambala"
        response = fa_client.patch(
            f"/devices/{port}?new_name={new_name}",
        )
        assert response.status_code == status.HTTP_200_OK

        response = fa_client.get(
            "/devices",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["devices"][0]["device_name"] == new_name


def test_get_device(fa_client: TestClient):
    expected_devices = DeviceConnectionSampler().list_of_samples(length=1)
    device = expected_devices[0]

    with stored_devices(expected_devices, fa_client.app.state.device_service):
        response = fa_client.get(f"/devices/{device.mqtt.port}")
        device = response.json()
        assert device["device_name"] == device["device_name"]
        assert device["device_id"] == str(device["port"])
        assert device["description"] == device["device_name"]
        assert device["internal_device_id"] == device["device_id"]
        assert device["inactivity_timeout"] == 0
        assert device["device_groups"] == []


def test_get_device_missing_device(fa_client: TestClient):
    expected_devices = DeviceConnectionSampler().list_of_samples(length=1)
    with stored_devices(expected_devices, fa_client.app.state.device_service):
        impossible_device_id = -1000
        response = fa_client.get(f"/devices/{impossible_device_id}")
        assert response.status_code == 404
        rpc_response = response.json()
        assert (
            rpc_response["message"]
            == f"Device with id {impossible_device_id} not found."
        )


@pytest.mark.parametrize(
    "device_id, module_id, ppl_parameter",
    [
        (
            42,
            "module_id_1",
            {
                "PPL_Parameters": {
                    "header": {"id": "00", "version": "01.01.00"},
                    "max_predictions": 3,
                    "dnn_output_classes": 5,
                }
            },
        ),
        (
            42,
            "module_id_1",
            {
                "PPL_Parameters": {
                    "header": {"id": "00", "version": "01.01.00"},
                    "dnn_output_detections": 10,
                    "max_detections": 2,
                    "threshold": 0.3,
                    "input_width": 300,
                    "input_height": 300,
                }
            },
        ),
    ],
)
@patch("local_console.fastapi.routes.devices.controller.DevicesController.configure")
def test_update_module_configuration_sample_apps(
    mocked_method: AsyncMock, fa_client: TestClient, device_id, module_id, ppl_parameter
):
    properties = {"property": {"configuration": ppl_parameter}}

    ConfigurationUpdateInDTO.model_validate(properties)

    response = fa_client.patch(
        f"/devices/{device_id}/modules/{module_id}",
        json=properties,
    )

    expected_result = {"result": "SUCCESS", "property": properties["property"]}

    assert response.status_code == 200
    assert response.json() == expected_result

    expected_arguments = PropertyInfo.model_validate(properties["property"])
    mocked_method.assert_awaited_once_with(
        device_id=device_id, module_id=module_id, property_info=expected_arguments
    )
