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
import base64
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from local_console.core.camera.enums import ConnectionState
from local_console.core.camera.schemas import DeviceStateInformation
from local_console.core.config import Config
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes
from local_console.core.schemas.schemas import DeviceConnection
from local_console.core.schemas.schemas import DeviceID
from local_console.core.schemas.schemas import GlobalConfiguration
from local_console.fastapi.routes.commons import EmptySuccess
from local_console.fastapi.routes.devices.controller import DevicesController
from local_console.fastapi.routes.devices.dto import DevicePostDTO
from pydantic import ValidationError

from tests.fixtures.devices import stored_devices
from tests.fixtures.devices import unmocked_device_service
from tests.mocks.config import set_configuration
from tests.mocks.devices import mocked_device_services
from tests.strategies.samplers.configs import GlobalConfigurationSampler


def _encodeId(device_port: int) -> str:
    return base64.b64encode(str(device_port).encode("utf-8")).decode("utf-8")


def assert_adapted(dto: DeviceStateInformation, sample: DeviceConnection) -> None:
    assert dto.device_name == sample.name
    assert dto.description == dto.device_name
    assert dto.device_id == str(sample.mqtt.port)
    assert dto.internal_device_id == dto.device_id
    assert dto.inactivity_timeout == 0
    assert dto.connection_state == ConnectionState.DISCONNECTED


@pytest.mark.trio
async def test_controller_list(mocked_agent_fixture) -> None:
    config_sample = GlobalConfigurationSampler().sample()
    device_services = mocked_device_services()
    set_configuration(config_sample)
    config_obj = Config()
    await device_services.init_devices(config_sample.devices)

    controller = DevicesController(config_obj, device_services)
    result = controller.list_devices(length=len(config_sample.devices))

    assert len(config_sample.devices) == len(result.devices)
    for i, sample in enumerate(config_sample.devices):
        assert_adapted(result.devices[i], sample)


@pytest.mark.trio
async def test_list_pagination_return_all(mocked_agent_fixture):
    config_sample = GlobalConfigurationSampler().sample()
    set_configuration(config_sample)
    mocked_config = Config()

    device_services = mocked_device_services()
    async with stored_devices(config_sample.devices, device_services):
        controller = DevicesController(mocked_config, device_services)

        result = controller.list_devices(length=len(config_sample.devices))

        assert len(config_sample.devices) == len(result.devices)
        assert result.continuation_token == ""


@pytest.mark.trio
async def test_list_paginated_result(mocked_agent_fixture):
    config_sample = GlobalConfigurationSampler(num_of_devices=5).sample()
    set_configuration(config_sample)
    mocked_config = Config()

    device_services = mocked_device_services()
    async with stored_devices(config_sample.devices, device_services):
        controller = DevicesController(mocked_config, device_services)

        result = controller.list_devices(length=4)

        assert len(result.devices) == 4
        assert result.continuation_token == _encodeId(
            config_sample.devices[4].mqtt.port
        )


@pytest.mark.trio
async def test_list_next_result(mocked_agent_fixture):
    config_sample = GlobalConfigurationSampler(num_of_devices=5).sample()
    continuation_token = _encodeId(config_sample.devices[4].mqtt.port)
    set_configuration(config_sample)
    mocked_config = Config()

    device_services = mocked_device_services()
    async with stored_devices(config_sample.devices, device_services):
        controller = DevicesController(mocked_config, device_services)

        result = controller.list_devices(
            length=4, continuation_token=continuation_token
        )
        assert len(result.devices) == 1
        assert result.continuation_token == ""
        assert_adapted(result.devices[0], config_sample.devices[4])


@pytest.mark.trio
async def test_get_device_missing_value(mocked_agent_fixture):
    config_sample = GlobalConfigurationSampler().sample()
    set_configuration(config_sample)
    mocked_config = Config()

    device_services = mocked_device_services()
    controller = DevicesController(mocked_config, device_services)

    device_id = -1000
    with pytest.raises(UserException) as e:
        controller.get_device(device_id)

    assert str(e.value) == f"Device with id {device_id} not found."
    assert e.value.code == ErrorCodes.EXTERNAL_DEVICE_NOT_FOUND


@pytest.mark.trio
async def test_controller_delete() -> None:
    config_sample = GlobalConfigurationSampler().sample()
    set_configuration(config_sample)
    config_obj = Config()
    device_services = mocked_device_services()

    async with stored_devices(config_sample.devices, device_services):
        len_with_device = len(config_obj.data.devices)

        device_to_delete = config_sample.devices[1].mqtt.port
        controller = DevicesController(config_obj, device_services)
        controller.delete(device_id=device_to_delete)

        assert len(config_obj.data.devices) == len_with_device - 1
        assert all(
            device.mqtt.port != device_to_delete for device in config_obj.data.devices
        )


@pytest.mark.trio
async def test_controller_delete_stop_trio(mocked_agent_fixture):
    config_sample = GlobalConfigurationSampler().sample()
    set_configuration(config_sample)
    mocked_config = Config()

    device_to_delete = config_sample.devices[1]
    device_service = mocked_device_services()
    async with stored_devices(config_sample.devices, device_service):
        state = device_service.get_camera(device_to_delete.id)
        state._started.set()
        with patch.object(state, "_cancel_scope"):
            controller = DevicesController(mocked_config, device_service)
            controller.delete(device_id=device_to_delete.id)
            state._cancel_scope.cancel.assert_called_once()


@pytest.mark.trio
async def test_list_next_with_continuation(mocked_agent_fixture):
    config_sample = GlobalConfigurationSampler(num_of_devices=5).sample()
    continuation_token = _encodeId(config_sample.devices[2].mqtt.port)
    set_configuration(config_sample)
    mocked_config = Config()

    device_services = mocked_device_services()
    async with stored_devices(config_sample.devices, device_services):
        controller = DevicesController(mocked_config, device_services)

        result = controller.list_devices(
            length=2, continuation_token=continuation_token
        )

        assert len(result.devices) == 2
        expected_continuation = _encodeId(config_sample.devices[4].mqtt.port)
        assert result.continuation_token == expected_continuation


@pytest.mark.trio
async def test_list_paginated_result_with_empty_continuation(mocked_agent_fixture):
    config_sample = GlobalConfigurationSampler(num_of_devices=5).sample()
    set_configuration(config_sample)
    mocked_config = Config()

    device_services = mocked_device_services()
    async with stored_devices(config_sample.devices, device_services):
        controller = DevicesController(mocked_config, device_services)

        result = controller.list_devices(length=4, continuation_token="")
        assert len(result.devices) == 4
        assert result.continuation_token == _encodeId(
            config_sample.devices[4].mqtt.port
        )


@pytest.mark.trio
async def test_list_paginated_result_with_invalid_continuation(mocked_agent_fixture):
    config_sample = GlobalConfigurationSampler(num_of_devices=5).sample()
    set_configuration(config_sample)
    mocked_config = Config()

    device_services = mocked_device_services()
    async with stored_devices(config_sample.devices, device_services):
        controller = DevicesController(mocked_config, device_services)

        result = controller.list_devices(length=4, continuation_token="__[]__")
        assert len(result.devices) == 4
        assert result.continuation_token == _encodeId(
            config_sample.devices[4].mqtt.port
        )


@pytest.mark.trio
async def test_list_all_connection_state() -> None:
    num_devices: int = 3
    config_sample = GlobalConfigurationSampler(num_of_devices=num_devices).sample()
    set_configuration(config_sample)
    mocked_config = Config()

    device_services = mocked_device_services()
    async with stored_devices(config_sample.devices, device_services):
        controller = DevicesController(mocked_config, device_services)

        result_1 = controller.list_devices()
        assert len(result_1.devices) == num_devices

        result_2 = controller.list_devices(connection_state=None)
        assert len(result_2.devices) == num_devices


@pytest.mark.trio
async def test_create_calls_device() -> None:
    device_service = MagicMock()
    device_service.add_device = AsyncMock()
    input = DevicePostDTO(device_name="device", id=DeviceID(1883))

    controller = DevicesController(MagicMock(), device_service=device_service)
    result = await controller.create(input)

    device_service.add_device.assert_called_once_with(input.device_name, input.id)
    assert result == EmptySuccess()


@pytest.mark.trio
async def test_create_raise_error_port_already_taken() -> None:
    # device_service starts with the default device at port 1883 ...
    async with unmocked_device_service() as device_service:
        # ...and this will attempt to create a new one on the same port.
        input_spec = DevicePostDTO(
            device_name="newdevice", id=DeviceID(1883), port=1883
        )
        controller = DevicesController(MagicMock(), device_service=device_service)
        with pytest.raises(UserException) as error:
            await controller.create(input_spec)

        assert error.value.code == ErrorCodes.EXTERNAL_DEVICE_PORTS_MUST_BE_UNIQUE
        assert error.value.args[0] == f"Specified port {input_spec.id} is already taken"


@pytest.mark.trio
async def test_create_raise_error_port_out_of_range() -> None:
    # device_service starts with the default device at port 1883 ...
    async with unmocked_device_service() as device_service:
        # ...and this will attempt to create a new one on an unsupported port.
        input_spec = DevicePostDTO(device_name="device", id=DeviceID(65536))
        controller = DevicesController(MagicMock(), device_service=device_service)
        with pytest.raises(UserException) as error:
            await controller.create(input_spec)

        assert error.value.code == ErrorCodes.EXTERNAL_DEVICE_PORTS_MUST_BE_IN_TCP_RANGE
        assert error.value.args[0] == "MQTT port should be less than or equal to 65535"


@pytest.mark.trio
async def test_create_raise_error_other_error(
    single_device_config: GlobalConfiguration,
) -> None:
    with patch("local_console.core.config.DeviceConnection") as mock_add:
        mock_add.side_effect = ValidationError.from_exception_data(
            "Foobar",
            [{"type": "json_type", "loc": ("a", 2), "input": 4, "ctx": {"gt": 5}}],
        )
        async with unmocked_device_service() as device_service:
            input_spec = DevicePostDTO(
                device_name="device", id=DeviceID(1884), port=1884
            )
            controller = DevicesController(MagicMock(), device_service=device_service)
            with pytest.raises(UserException) as error:
                await controller.create(input_spec)

            assert error.value.code == ErrorCodes.EXTERNAL_DEVICE_CREATION_VALIDATION


@pytest.mark.trio
async def test_create_raise_error_port_already_in_use() -> None:
    with patch(
        "local_console.core.device_services.is_port_open",
        return_value=True,
    ):
        # device_service starts with the default device at port 1883 ...
        async with unmocked_device_service() as device_service:
            # ...and this will attempt to create a new one on a port that is already in use
            input_spec = DevicePostDTO(device_name="device", id=DeviceID(8000))
            controller = DevicesController(MagicMock(), device_service=device_service)
            with pytest.raises(UserException) as error:
                await controller.create(input_spec)

            assert error.value.code == ErrorCodes.EXTERNAL_DEVICE_PORT_ALREADY_IN_USE
