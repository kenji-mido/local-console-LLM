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
from httpx import AsyncClient
from local_console.core.device_services import DeviceServices
from local_console.core.schemas.schemas import DeviceID
from local_console.fastapi.routes.commons import EmptySuccess
from local_console.fastapi.routes.devices.controller import DevicesController
from local_console.fastapi.routes.devices.dependencies import devices_controller
from local_console.fastapi.routes.devices.dto import DeviceListDTO
from local_console.fastapi.routes.devices.dto import DevicePostDTO
from local_console.fastapi.routes.devices.dto import PropertyInfo
from local_console.fastapi.routes.devices.dto import RPCRequestDTO
from local_console.fastapi.routes.devices.dto import RPCResponseDTO
from local_console.fastapi.routes.devices.router import create_device
from local_console.fastapi.routes.devices.router import delete_device
from local_console.fastapi.routes.devices.router import device_module_rpc
from local_console.fastapi.routes.devices.router import device_rpc
from local_console.fastapi.routes.devices.router import get_devices

from tests.fixtures.devices import stored_devices
from tests.mocks.mock_paho_mqtt import MockMqttAgent
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
        starting_after=continuation_token,
        controller=devices_controller,
    )

    devices_controller.list_devices.assert_called_once_with(
        length=length, continuation_token=continuation_token, connection_state=None
    )
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
        extra=None,
    )
    device_id: int = 1

    devices_controller.rpc.return_value = expected

    result = await device_rpc(
        device_id=device_id, rpc_args=request, controller=devices_controller
    )

    devices_controller.rpc.assert_awaited_once_with(device_id, "$system", request)
    assert result is expected


@pytest.mark.trio
async def test_module_rpc_calls_controller() -> None:
    devices_controller = AsyncMock()
    expected = RPCResponseDTO(command_response={"image": "base64Image"})
    request = RPCRequestDTO(
        command_name="direct_get_image",
        parameters={"sensor_name": "IMX500", "crop_h_offset": 0},
        extra=None,
    )
    device_id: int = 1

    devices_controller.rpc.return_value = expected

    module_id = "my-module"
    result = await device_module_rpc(
        device_id=device_id,
        rpc_args=request,
        controller=devices_controller,
        module_id=module_id,
    )

    devices_controller.rpc.assert_awaited_once_with(device_id, module_id, request)
    assert result is expected


@pytest.mark.trio
async def test_create_calls_controller() -> None:
    devices_controller = AsyncMock()
    input = DevicePostDTO(device_name="device", id=DeviceID(1883))
    expected = EmptySuccess()

    devices_controller.create.return_value = expected

    result = await create_device(device=input, controller=devices_controller)

    devices_controller.create.assert_called_once_with(input)
    assert result is expected


@pytest.mark.trio
async def test_crud_test(
    fa_client_with_agent: AsyncClient, mocked_agent_fixture: MockMqttAgent
) -> None:
    expected_devices = DeviceConnectionSampler().list_of_samples()
    device_service: DeviceServices = (
        fa_client_with_agent._transport.app.state.device_service
    )
    expected_len = len(expected_devices)
    max_port = max([dev.mqtt.port for dev in expected_devices]) + 1
    async with stored_devices(expected_devices, device_service):
        response = await fa_client_with_agent.get("/devices?limit=500")
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

        response = await fa_client_with_agent.post(
            "/devices",
            json={"device_name": f"new_device_{max_port}", "id": max_port},
        )

        assert response.status_code == 200
        assert response.json()["result"] == "SUCCESS"

        response = await fa_client_with_agent.delete(f"/devices/{max_port}")
        assert response.status_code == 200
        assert response.json()["result"] == "SUCCESS"

        response = await fa_client_with_agent.get("/devices?limit=500")
        assert response.status_code == 200

        assert len(response.json()["devices"]) == expected_len
        mocked_agent_fixture.stop_receiving_messages()


@pytest.mark.trio
async def test_delete_last_device(
    fa_client_with_agent: AsyncClient, mocked_agent_fixture: MockMqttAgent
) -> None:
    expected_devices = DeviceConnectionSampler().list_of_samples()
    device_service: DeviceServices = (
        fa_client_with_agent._transport.app.state.device_service
    )
    expected_devices = DeviceConnectionSampler().list_of_samples(1)
    device = expected_devices[0]
    async with stored_devices(expected_devices, device_service):
        response = await fa_client_with_agent.delete(f"/devices/{device.mqtt.port}")
        assert response.status_code == status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE
        assert response.json()["result"] == "ERROR"
        assert response.json()["message"] == "You need at least one device to work with"
        assert response.json()["code"] == "120001"
        mocked_agent_fixture.stop_receiving_messages()


def test_get_image(fa_client: TestClient) -> None:
    mock_controller = AsyncMock(spec=DevicesController)
    fa_client.app.dependency_overrides[devices_controller] = lambda: mock_controller
    image = "test_get_image_result"
    mocked_response = RPCResponseDTO(command_response={"image": image})
    mock_controller.rpc.return_value = mocked_response
    response = fa_client.post(
        "/devices/1883/command",
        json={
            "command_name": "direct_get_image",
            "parameters": {
                "sensor_name": "IMX500",
                "crop_h_offset": 0,
                "crop_v_offset": 0,
                "crop_h_size": 2028,
                "crop_v_size": 1520,
            },
        },
    )
    mock_controller.rpc.assert_awaited_once()
    assert response.status_code == 200
    rpc_response = response.json()
    assert rpc_response["result"] == "SUCCESS"
    assert rpc_response["command_response"]["image"] == image


@pytest.mark.trio
async def test_get_image_not_found(
    fa_client_async: AsyncClient, mocked_agent_fixture: MockMqttAgent
) -> None:
    expected_devices = DeviceConnectionSampler().list_of_samples(length=1)
    expected_devices[0].mqtt.port = 1883

    device_service: DeviceServices = fa_client_async._transport.app.state.device_service
    async with stored_devices(expected_devices, device_service):

        response = await fa_client_async.post(
            "/devices/1884/command",
            json={
                "command_name": "direct_get_image",
                "parameters": {
                    "sensor_name": "IMX500",
                    "crop_h_offset": 0,
                    "crop_v_offset": 0,
                    "crop_h_size": 2028,
                    "crop_v_size": 1520,
                },
            },
        )
        assert response.status_code == 404
        rpc_response = response.json()
        assert rpc_response["result"] == "ERROR"
        assert rpc_response["message"] == "Could not find device 1884"
        mocked_agent_fixture.stop_receiving_messages()


@patch("local_console.fastapi.routes.devices.controller.DevicesController.configure")
def test_update_module_configuration(mocked_method: AsyncMock, fa_client: TestClient):
    device_id = 42
    module_id = "module_id_1"
    property_name = "property_name_1"
    key = "key_1"
    value = "value_1"

    configuration = {property_name: {key: value}}
    payload = {"configuration": configuration}
    response = fa_client.patch(
        f"/devices/{device_id}/modules/{module_id}/property",
        json=payload,
    )

    assert response.status_code == 200
    assert response.json() == {"result": "SUCCESS", **payload}

    mocked_method.assert_awaited_once_with(
        device_id=device_id,
        module_id=module_id,
        property_info=PropertyInfo(configuration=configuration),
    )


@pytest.mark.trio
async def test_device_renaming(
    fa_client_with_agent: AsyncClient, mocked_agent_fixture: MockMqttAgent
) -> None:
    device_service: DeviceServices = (
        fa_client_with_agent._transport.app.state.device_service
    )
    expected_devices = DeviceConnectionSampler().list_of_samples(length=1)
    port = expected_devices[0].mqtt.port
    async with stored_devices(expected_devices, device_service):
        new_name = "shambala"
        response = await fa_client_with_agent.patch(
            f"/devices/{port}?new_name={new_name}",
        )
        assert response.status_code == status.HTTP_200_OK

        response = await fa_client_with_agent.get(
            "/devices",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["devices"][0]["device_name"] == new_name


@pytest.mark.trio
async def test_get_device(
    fa_client_with_agent: AsyncClient, mocked_agent_fixture: MockMqttAgent
) -> None:
    expected_devices = DeviceConnectionSampler().list_of_samples()
    device_service: DeviceServices = (
        fa_client_with_agent._transport.app.state.device_service
    )
    expected_devices = DeviceConnectionSampler().list_of_samples(length=1)
    expected_device = expected_devices[0]

    async with stored_devices(expected_devices, device_service):
        response = await fa_client_with_agent.get(
            f"/devices/{expected_device.mqtt.port}"
        )
        device = response.json()
        assert device["device_name"] == expected_device.name
        assert device["device_id"] == str(expected_device.mqtt.port)
        assert device["description"] == expected_device.name
        assert device["internal_device_id"] == str(expected_device.mqtt.port)
        assert device["inactivity_timeout"] == 0
        mocked_agent_fixture.stop_receiving_messages()


@pytest.mark.trio
async def test_get_device_missing_device(
    fa_client_with_agent: AsyncClient,
) -> None:
    expected_devices = DeviceConnectionSampler().list_of_samples()
    device_service: DeviceServices = (
        fa_client_with_agent._transport.app.state.device_service
    )
    expected_devices = DeviceConnectionSampler().list_of_samples(length=1)
    async with stored_devices(expected_devices, device_service):
        impossible_device_id = 100000
        response = await fa_client_with_agent.get(f"/devices/{impossible_device_id}")
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
    payload = {"configuration": ppl_parameter}

    response = fa_client.patch(
        f"/devices/{device_id}/modules/{module_id}/property",
        json=payload,
    )
    assert response.status_code == 200
    assert response.json() == {"result": "SUCCESS", **payload}

    mocked_method.assert_awaited_once_with(
        device_id=device_id,
        module_id=module_id,
        property_info=PropertyInfo(configuration=ppl_parameter),
    )


@patch("local_console.fastapi.routes.devices.controller.DevicesController.configure")
def test_update_device_configuration(mocked_method: AsyncMock, fa_client: TestClient):
    device_id = 42
    property_name = "property_name_1"
    key = "key_1"
    value = "value_1"

    configuration = {property_name: {key: value}}
    payload = {"configuration": configuration}
    response = fa_client.patch(
        f"/devices/{device_id}/property",
        json=payload,
    )

    assert response.status_code == 200
    assert response.json() == {"result": "SUCCESS", **payload}

    mocked_method.assert_awaited_once_with(
        device_id=device_id,
        module_id="$system",
        property_info=PropertyInfo(configuration=configuration),
    )


@pytest.mark.trio
async def test_get_module_id_property(
    fa_client_with_agent: AsyncClient,
):
    payload = {"node": {"property1": "value1"}, "another_module": {}}

    device_service: DeviceServices = (
        fa_client_with_agent._transport.app.state.device_service
    )
    camera = device_service.get_camera(1883)
    camera._common_properties.reported.edge_app = payload

    response = await fa_client_with_agent.get(
        "/devices/1883/modules/node/property",
    )
    assert response.status_code == 200
    assert response.json() == {"state": {"edge_app": payload["node"]}}
