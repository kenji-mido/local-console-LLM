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
import json
from collections.abc import Generator
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi import status
from local_console.clients.command.rpc import RPCArgument
from local_console.clients.command.rpc_with_response import RPCResponse
from local_console.core.camera.enums import ConnectionState
from local_console.core.camera.schemas import DeviceStateInformation
from local_console.core.camera.schemas import ModuleInfo
from local_console.core.camera.schemas import MProperty
from local_console.core.camera.schemas import MSAIModel
from local_console.core.camera.schemas import MSDeviceInfo
from local_console.core.camera.schemas import MSDeviceState
from local_console.core.camera.schemas import MSInfo
from local_console.core.camera.schemas import MSNetworkSettings
from local_console.core.camera.schemas import MSPeriodicSetting
from local_console.core.camera.schemas import MSPrivateEndpointSettings
from local_console.core.camera.schemas import MSSSIDSetting
from local_console.core.camera.schemas import MState
from local_console.core.camera.schemas import MSWirelessSetting
from local_console.core.camera.state import CameraState
from local_console.core.config import config_obj
from local_console.core.device_services import device_to_dto
from local_console.core.device_services import DeviceServices
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.core.schemas.schemas import DeviceConnection
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.fastapi.routes.commons import EmptySuccess
from local_console.fastapi.routes.devices.controller import DevicesController
from local_console.fastapi.routes.devices.controller import direct_command_translator
from local_console.fastapi.routes.devices.dto import DevicePostDTO
from pydantic import ValidationError

from tests.fixtures.agent import mocked_agent_fixture
from tests.fixtures.configs import stored_devices
from tests.fixtures.devices import with_real_device_service
from tests.mocks.devices import mocked_device_services
from tests.mocks.mock_configs import config_without_io
from tests.mocks.mock_configs import ConfigMocker
from tests.mocks.mock_paho_mqtt import MockMqttAgent
from tests.strategies.samplers.configs import ConfigSampler
from tests.strategies.samplers.configs import DeviceConnectionSampler
from tests.strategies.samplers.configs import GlobalConfigurationSampler
from tests.strategies.samplers.configs import MQTTParamsSampler
from tests.strategies.samplers.configs import PropertySampler
from tests.strategies.samplers.device_config import DeviceConfigurationSampler
from tests.strategies.samplers.fastapi import RPCRequestDTOSampler


def assert_adapted(dto: DeviceStateInformation, sample: DeviceConnection) -> None:
    assert dto.device_name == sample.name
    assert dto.description == dto.device_name
    assert dto.device_id == str(sample.mqtt.port)
    assert dto.internal_device_id == dto.device_id
    assert dto.port == sample.mqtt.port
    assert dto.inactivity_timeout == 0
    assert dto.device_groups == []
    assert dto.connection_state == ConnectionState.DISCONNECTED


def test_device_adapter() -> None:
    camera_state = CameraState(MagicMock(), MagicMock())
    camera_state.is_connected = ConnectionState.DISCONNECTED
    camera_state.device_config = None

    device_connection_sample = DeviceConnectionSampler().sample()

    device_configuration: DeviceConfiguration = DeviceConfigurationSampler().sample()

    dto = device_to_dto(
        device_connection=device_connection_sample,
        device_config=device_configuration,
        conn_state=ConnectionState.DISCONNECTED,
    )

    assert_adapted(dto, device_connection_sample)


def test_controller_list() -> None:
    config_sample = GlobalConfigurationSampler().sample()
    device_services = mocked_device_services()
    device_services.init_devices(config_sample.devices)
    with config_without_io(config_sample) as mocked_config:

        controller = DevicesController(mocked_config, device_services)

        result = controller.list_devices(length=len(config_sample.devices))

        assert len(config_sample.devices) == len(result.devices)
        for i, sample in enumerate(config_sample.devices):
            assert_adapted(result.devices[i], sample)


@pytest.mark.parametrize(
    "state",
    [
        None,
        "Idle",
        "Aborted",
        "InstallationMode",
        "PowerSaving",
        "FactoryReset",
        "FactoryResetDone",
    ],
)
def test_msdevice_state(state):
    MSDeviceState(process_state=state)


@pytest.mark.parametrize(
    "invalid_state",
    [
        "",
        "*****",
        1,
        "idle",
        "Installation Mode",
        "factoryreset",
        "random string",
    ],
)
def test_msdevice_state_fail(invalid_state):
    with pytest.raises(ValueError):
        MSDeviceState(process_state=invalid_state)


def module_sample() -> (
    Generator[tuple[DeviceConfiguration, list[ModuleInfo] | None], None, None]
):
    sampler = DeviceConfigurationSampler()
    configuration = sampler.sample()
    yield configuration, [
        ModuleInfo(
            property=MProperty(
                state=MState(
                    device_info=MSDeviceInfo(
                        processors=[
                            MSInfo(firmware_version=configuration.Version.ApFwVersion)
                        ],
                        sensors=[
                            MSInfo(
                                name=configuration.Hardware.Sensor,
                                firmware_version=configuration.Version.SensorFwVersion,
                                loader_version=configuration.Version.SensorLoaderVersion,
                            )
                        ],
                        ai_models=[
                            MSAIModel(
                                name=model_info[6:12],
                                version=model_info[12:],
                                converter_version=model_info[:6],
                            )
                            for model_info in configuration.Version.DnnModelVersion
                        ],
                    ),
                    device_state=MSDeviceState(
                        process_state=configuration.Status.ApplicationProcessor
                    ),
                    periodic_setting=MSPeriodicSetting(ip_addr_setting="save"),
                    network_settings=MSNetworkSettings(
                        ntp_url=configuration.Network.NTP,
                        gateway_address=configuration.Network.Gateway,
                        subnet_mask=configuration.Network.SubnetMask,
                        ip_address=configuration.Network.IPAddress,
                        dns_address=configuration.Network.DNS,
                        proxy_url=configuration.Network.ProxyURL,
                        proxy_port=configuration.Network.ProxyPort,
                        proxy_user_name=configuration.Network.ProxyUserName,
                    ),
                    wireless_setting=MSWirelessSetting(
                        sta_mode_setting=MSSSIDSetting(ssid=None, password=None)
                    ),
                    PRIVATE_endpoint_settings=MSPrivateEndpointSettings(
                        endpoint_url="localhost", endpoint_port=1883
                    ),
                )
            )
        )
    ]


@pytest.mark.parametrize(["configuration", "expected"], module_sample())
def test_get_device(
    configuration: DeviceConfiguration, expected: list[ModuleInfo]
) -> None:
    config_sample = GlobalConfigurationSampler(
        num_of_devices=1,
        devices=DeviceConnectionSampler(
            mqtt_sampler=MQTTParamsSampler(host="localhost")
        ),
    ).sample()
    device = config_sample.devices[0]
    device_service = DeviceServices(MagicMock(), MagicMock(), MagicMock)
    device_service.add_device_to_internals(device)
    device_service.states[device.mqtt.port].device_config.value = configuration

    with ConfigMocker.mock_configuration(config_sample) as mocked_config:
        controller = DevicesController(mocked_config, device_service)

        device_id = device.mqtt.port
        result: DeviceStateInformation = controller.get_device(device_id)

        assert result.modules == expected


def test_get_device_missing_value():
    config_sample = GlobalConfigurationSampler().sample()
    device_services = mocked_device_services()
    with ConfigMocker.mock_configuration(
        config_sample, device_services
    ) as mocked_config:
        controller = DevicesController(mocked_config, device_services)

        device_id = -1000

        with pytest.raises(UserException) as e:
            controller.get_device(device_id)

        assert str(e.value) == f"Device with id {device_id} not found."
        assert e.value.code == ErrorCodes.EXTERNAL_DEVICE_NOT_FOUND


def test_controller_delete() -> None:
    config_sample = GlobalConfigurationSampler().sample()
    with stored_devices(config_sample.devices):

        len_with_device = len(config_obj.config.devices)
        device_to_delete = config_sample.devices[1].mqtt.port
        device_service = mocked_device_services()
        for device in config_sample.devices:
            device_service.add_device_to_internals(device)
        controller = DevicesController(config_obj, device_service)

        controller.delete(device_id=device_to_delete)

        assert len(config_obj.config.devices) == len_with_device - 1
        assert all(
            device.mqtt.port != device_to_delete for device in config_obj.config.devices
        )


def test_controller_delete_stop_trio(mocked_agent_fixture) -> None:
    config_sample = GlobalConfigurationSampler().sample()
    device_service = mocked_device_services()
    with ConfigMocker.mock_configuration(
        config_sample, device_service
    ) as mocked_config:
        device_to_delete = config_sample.devices[1]
        device_service.add_device_to_internals(device_to_delete)
        state = device_service.states[device_to_delete.mqtt.port]
        state._started.set()
        with patch.object(state, "_cancel_scope"):
            controller = DevicesController(mocked_config, device_service)
            controller.delete(device_id=device_to_delete.mqtt.port)
            state._cancel_scope.cancel.assert_called_once()


def test_list_pagination_return_all() -> None:
    config_sample = GlobalConfigurationSampler().sample()
    device_services = mocked_device_services()
    with ConfigMocker.mock_configuration(
        config_sample, device_services
    ) as mocked_config:

        controller = DevicesController(mocked_config, device_services)

        result = controller.list_devices(length=len(config_sample.devices))

        assert len(config_sample.devices) == len(result.devices)
        assert result.continuation_token == ""


def test_list_paginated_result() -> None:
    config_sample = GlobalConfigurationSampler(num_of_devices=5).sample()
    device_services = mocked_device_services()
    with ConfigMocker.mock_configuration(
        config_sample, device_services
    ) as mocked_config:

        controller = DevicesController(mocked_config, device_services)

        result = controller.list_devices(length=4)

        assert len(result.devices) == 4
        assert result.continuation_token == _encodeId(
            config_sample.devices[4].mqtt.port
        )


def test_list_next_result() -> None:
    config_sample = GlobalConfigurationSampler(num_of_devices=5).sample()
    continuation_token = _encodeId(config_sample.devices[4].mqtt.port)
    device_services = mocked_device_services()
    with ConfigMocker.mock_configuration(
        config_sample, device_services
    ) as mocked_config:

        controller = DevicesController(mocked_config, device_services)

        result = controller.list_devices(
            length=4, continuation_token=continuation_token
        )

        assert len(result.devices) == 1
        assert result.continuation_token == ""
        assert_adapted(result.devices[0], config_sample.devices[4])


def test_list_next_with_continuation() -> None:
    config_sample = GlobalConfigurationSampler(num_of_devices=5).sample()
    continuation_token = _encodeId(config_sample.devices[2].mqtt.port)
    device_services = mocked_device_services()
    with ConfigMocker.mock_configuration(
        config_sample, device_services
    ) as mocked_config:

        controller = DevicesController(mocked_config, device_services)

        result = controller.list_devices(
            length=2, continuation_token=continuation_token
        )

        assert len(result.devices) == 2
        expected_continuation = _encodeId(config_sample.devices[4].mqtt.port)
        assert result.continuation_token == expected_continuation


def test_list_paginated_result_with_empty_continuation() -> None:
    config_sample = GlobalConfigurationSampler(num_of_devices=5).sample()
    device_services = mocked_device_services()
    with ConfigMocker.mock_configuration(
        config_sample, device_services
    ) as mocked_config:

        controller = DevicesController(mocked_config, device_services)

        result = controller.list_devices(length=4, continuation_token="")

        assert len(result.devices) == 4
        assert result.continuation_token == _encodeId(
            config_sample.devices[4].mqtt.port
        )


def test_list_paginated_result_with_invalid_continuation() -> None:
    config_sample = GlobalConfigurationSampler(num_of_devices=5).sample()
    device_services = mocked_device_services()
    with ConfigMocker.mock_configuration(
        config_sample, device_services
    ) as mocked_config:

        controller = DevicesController(mocked_config, device_services)

        result = controller.list_devices(length=4, continuation_token="__[]__")

        assert len(result.devices) == 4
        assert result.continuation_token == _encodeId(
            config_sample.devices[4].mqtt.port
        )


def modules_samples() -> (
    Generator[tuple[DeviceConfiguration, list[ModuleInfo] | None], None, None]
):
    sampler = DeviceConfigurationSampler()
    configuration = sampler.sample()
    yield configuration, [
        ModuleInfo(
            property=MProperty(
                state=MState(
                    device_info=MSDeviceInfo(
                        processors=[
                            MSInfo(firmware_version=configuration.Version.ApFwVersion)
                        ],
                        sensors=[
                            MSInfo(
                                name=configuration.Hardware.Sensor,
                                firmware_version=configuration.Version.SensorFwVersion,
                                loader_version=configuration.Version.SensorLoaderVersion,
                            )
                        ],
                        ai_models=[
                            MSAIModel(
                                name=model_info[6:12],
                                version=model_info[12:],
                                converter_version=model_info[:6],
                            )
                            for model_info in configuration.Version.DnnModelVersion
                        ],
                    ),
                    device_state=MSDeviceState(
                        process_state=configuration.Status.ApplicationProcessor
                    ),
                    periodic_setting=MSPeriodicSetting(ip_addr_setting="save"),
                    network_settings=MSNetworkSettings(
                        ntp_url=configuration.Network.NTP,
                        gateway_address=configuration.Network.Gateway,
                        subnet_mask=configuration.Network.SubnetMask,
                        ip_address=configuration.Network.IPAddress,
                        dns_address=configuration.Network.DNS,
                        proxy_url=configuration.Network.ProxyURL,
                        proxy_port=configuration.Network.ProxyPort,
                        proxy_user_name=configuration.Network.ProxyUserName,
                    ),
                    wireless_setting=MSWirelessSetting(
                        sta_mode_setting=MSSSIDSetting(ssid=None, password=None)
                    ),
                    PRIVATE_endpoint_settings=MSPrivateEndpointSettings(
                        endpoint_url="localhost", endpoint_port=1883
                    ),
                )
            )
        )
    ]
    yield None, [
        ModuleInfo(
            property=MProperty(
                state=MState(
                    device_info=MSDeviceInfo(),
                    device_state=MSDeviceState(),
                    periodic_setting=MSPeriodicSetting(ip_addr_setting="dhcp"),
                    network_settings=MSNetworkSettings(),
                    wireless_setting=MSWirelessSetting(),
                    PRIVATE_endpoint_settings=MSPrivateEndpointSettings(
                        endpoint_url="localhost", endpoint_port=1883
                    ),
                )
            )
        )
    ]
    sampler.version.ApFwVersion = ""
    configuration = sampler.sample()
    yield configuration, [
        ModuleInfo(
            property=MProperty(
                state=MState(
                    device_info=MSDeviceInfo(
                        sensors=[
                            MSInfo(
                                name=configuration.Hardware.Sensor,
                                firmware_version=configuration.Version.SensorFwVersion,
                                loader_version=configuration.Version.SensorLoaderVersion,
                            )
                        ],
                        ai_models=[
                            MSAIModel(
                                name=model_info[6:12],
                                version=model_info[12:],
                                converter_version=model_info[:6],
                            )
                            for model_info in configuration.Version.DnnModelVersion
                        ],
                    ),
                    device_state=MSDeviceState(
                        process_state=configuration.Status.ApplicationProcessor
                    ),
                    periodic_setting=MSPeriodicSetting(ip_addr_setting="save"),
                    network_settings=MSNetworkSettings(
                        ntp_url=configuration.Network.NTP,
                        gateway_address=configuration.Network.Gateway,
                        subnet_mask=configuration.Network.SubnetMask,
                        ip_address=configuration.Network.IPAddress,
                        dns_address=configuration.Network.DNS,
                        proxy_url=configuration.Network.ProxyURL,
                        proxy_port=configuration.Network.ProxyPort,
                        proxy_user_name=configuration.Network.ProxyUserName,
                    ),
                    wireless_setting=MSWirelessSetting(
                        sta_mode_setting=MSSSIDSetting(ssid=None, password=None)
                    ),
                    PRIVATE_endpoint_settings=MSPrivateEndpointSettings(
                        endpoint_url="localhost", endpoint_port=1883
                    ),
                )
            )
        )
    ]
    sampler.version.ApFwVersion = "something"
    sampler.version.SensorFwVersion = ""
    configuration = sampler.sample()
    yield configuration, [
        ModuleInfo(
            property=MProperty(
                state=MState(
                    device_info=MSDeviceInfo(
                        processors=[
                            MSInfo(firmware_version=configuration.Version.ApFwVersion)
                        ],
                        ai_models=[
                            MSAIModel(
                                name=model_info[6:12],
                                version=model_info[12:],
                                converter_version=model_info[:6],
                            )
                            for model_info in configuration.Version.DnnModelVersion
                        ],
                    ),
                    device_state=MSDeviceState(
                        process_state=configuration.Status.ApplicationProcessor
                    ),
                    periodic_setting=MSPeriodicSetting(ip_addr_setting="save"),
                    network_settings=MSNetworkSettings(
                        ntp_url=configuration.Network.NTP,
                        gateway_address=configuration.Network.Gateway,
                        subnet_mask=configuration.Network.SubnetMask,
                        ip_address=configuration.Network.IPAddress,
                        dns_address=configuration.Network.DNS,
                        proxy_url=configuration.Network.ProxyURL,
                        proxy_port=configuration.Network.ProxyPort,
                        proxy_user_name=configuration.Network.ProxyUserName,
                    ),
                    wireless_setting=MSWirelessSetting(
                        sta_mode_setting=MSSSIDSetting(ssid=None, password=None)
                    ),
                    PRIVATE_endpoint_settings=MSPrivateEndpointSettings(
                        endpoint_url="localhost", endpoint_port=1883
                    ),
                )
            )
        )
    ]


@pytest.mark.parametrize(["configuration", "expected"], modules_samples())
def test_list_with_modules_info(
    configuration: DeviceConfiguration, expected: list[ModuleInfo] | None
) -> None:
    config_sample = GlobalConfigurationSampler(
        num_of_devices=1,
        devices=DeviceConnectionSampler(
            mqtt_sampler=MQTTParamsSampler(host="localhost")
        ),
    ).sample()

    device = config_sample.devices[0]
    device_service = DeviceServices(MagicMock(), MagicMock(), MagicMock)
    device_service.add_device_to_internals(device)
    device_service.states[device.mqtt.port].device_config.value = configuration

    with ConfigMocker.mock_configuration(config_sample) as mocked_config:
        controller = DevicesController(mocked_config, device_service)

        result = controller.list_devices()

        assert result.devices[0].modules == expected


@pytest.mark.trio
@patch(
    "local_console.fastapi.routes.devices.controller.lock_until_started", AsyncMock()
)
async def test_create_calls_device() -> None:
    device_service = MagicMock()
    input = DevicePostDTO(device_name="device", mqtt_port=1883)

    controller = DevicesController(MagicMock(), device_service=device_service)

    result = await controller.create(input)

    device_service.add_device.assert_called_once_with(
        input.device_name, input.mqtt_port
    )
    assert result == EmptySuccess()


@pytest.mark.parametrize(
    "input,result",
    [["direct_get_image", "DirectGetImage"], ["any_thing_else", "any_thing_else"]],
)
def test_direct_command_translator(input, result) -> None:
    assert direct_command_translator(input) == result


@pytest.mark.trio
@patch("local_console.clients.command.rpc_with_response.RPCWithResponse")
async def test_get_image(mock_rpc_with_response: AsyncMock) -> None:
    mocked_command = AsyncMock()
    mock_rpc_with_response.return_value = mocked_command
    image = "expectedImage"
    response = RPCResponse(
        topic="v1/devices/me/rpc/response/1",
        payload={
            "moduleInstance": "backdoor-EA_Main",
            "status": 0,
            "response": {"Result": "Succeeded", "Image": image},
        },
    )
    mocked_command.run.return_value = response
    device = DeviceConnectionSampler().sample()
    configuration = GlobalConfigurationSampler(num_of_devices=1).sample()

    with ConfigMocker.mock_configuration(configuration) as config:
        service = mocked_device_services()
        service.add_device_to_internals(device)
        service.states[device.mqtt.port].mqtt_client = AsyncMock()

        controller = DevicesController(config, service)

        request = RPCRequestDTOSampler().sample()

        result = await controller.rpc(device.mqtt.port, request)

        assert result.command_response["image"] == image
        mocked_command.run.assert_awaited_once_with(
            RPCArgument(
                onwire_schema=OnWireProtocol.EVP1,
                instance_id="backdoor-EA_Main",
                method="DirectGetImage",
                params={"some": "parameter"},
            )
        )


@pytest.mark.trio
async def test_get_image_invalid_schema() -> None:
    configuration_builder = GlobalConfigurationSampler(num_of_devices=1)
    configuration_builder.evp.platform = "invalid"
    config = ConfigSampler(config=configuration_builder).sample()
    device = config.config.devices[0]

    service = mocked_device_services()
    service.add_device_to_internals(device)
    controller = DevicesController(config, service)
    request = RPCRequestDTOSampler().sample()
    with pytest.raises(HTTPException) as error:
        await controller.rpc(device.mqtt.port, request)

    assert error.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert error.value.detail == "Server misconfiguration"


@pytest.mark.trio
async def test_create_raise_error_on_agent_error(
    mocked_agent_fixture: MockMqttAgent,
) -> None:
    # device_service starts with the default device at port 1883 ...
    async with with_real_device_service() as device_service:
        # ...we ensure the default devices are properly initialized...
        devices_in_config: [DeviceConnection] = config_obj.get_device_configs()
        device_service.init_devices(devices_in_config)
        # ...and this will attempt to create a new one a different port...
        device_info = DevicePostDTO(device_name="device", mqtt_port=9999)
        # ...but some error happens during agent instantiation.
        agent = mocked_agent_fixture
        agent.constructor.side_effect = Exception("Could not start")
        controller = DevicesController(MagicMock(), device_service=device_service)

        with pytest.raises(HTTPException) as error:
            await controller.create(device_info)

        assert error.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert (
            error.value.detail
            == f"Could not start server at port {device_info.mqtt_port}"
        )


@pytest.mark.trio
async def test_create_raise_error_port_already_taken() -> None:
    # device_service starts with the default device at port 1883 ...
    async with with_real_device_service() as device_service:
        # ...and this will attempt to create a new one on the same port.
        input_spec = DevicePostDTO(device_name="device", mqtt_port=1883)
        controller = DevicesController(MagicMock(), device_service=device_service)
        with pytest.raises(UserException) as error:
            await controller.create(input_spec)

        assert error.value.code == ErrorCodes.EXTERNAL_DEVICE_PORTS_MUST_BE_UNIQUE
        assert (
            error.value.args[0]
            == f"Specified port {input_spec.mqtt_port} is already taken"
        )


@pytest.mark.trio
async def test_create_raise_error_port_out_of_range() -> None:
    # device_service starts with the default device at port 1883 ...
    async with with_real_device_service() as device_service:
        # ...and this will attempt to create a new one on an unsupported port.
        input_spec = DevicePostDTO(device_name="device", mqtt_port=65536)
        controller = DevicesController(MagicMock(), device_service=device_service)
        with pytest.raises(UserException) as error:
            await controller.create(input_spec)

        assert error.value.code == ErrorCodes.EXTERNAL_DEVICE_PORTS_MUST_BE_IN_TCP_RANGE
        assert error.value.args[0] == "MQTT port should be less than or equal to 65535"


@pytest.mark.trio
async def test_create_raise_error_other_error() -> None:

    simple_conf = GlobalConfigurationSampler(num_of_devices=1).sample()
    with (
        config_without_io(simple_conf),
        patch("local_console.core.config.DeviceConnection") as mock_add,
    ):
        mock_add.side_effect = ValidationError.from_exception_data(
            "Foobar",
            [{"type": "json_type", "loc": ("a", 2), "input": 4, "ctx": {"gt": 5}}],
        )
        async with with_real_device_service() as device_service:
            input_spec = DevicePostDTO(device_name="device", mqtt_port=1884)
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
        async with with_real_device_service() as device_service:
            # ...and this will attempt to create a new one on a port that is already in use
            input_spec = DevicePostDTO(device_name="device", mqtt_port=8000)
            controller = DevicesController(MagicMock(), device_service=device_service)
            with pytest.raises(UserException) as error:
                await controller.create(input_spec)

            assert error.value.code == ErrorCodes.EXTERNAL_DEVICE_PORT_ALREADY_IN_USE


@pytest.mark.trio
async def test_configure() -> None:
    device = DeviceConnectionSampler().sample()
    configuration = GlobalConfigurationSampler(num_of_devices=1).sample()

    with ConfigMocker.mock_configuration(configuration) as config:
        service = mocked_device_services()
        service.add_device_to_internals(device)
        service.states[device.mqtt.port].mqtt_client = AsyncMock()
        mocked_configure = AsyncMock()
        service.states[device.mqtt.port].mqtt_client.configure = mocked_configure

        controller = DevicesController(config, service)

        module_id = "module_id_1"
        property_name = "property_name_1"
        property_key = "property_key_1"
        property_value = "property_value_1"

        property_content = {
            property_key: property_value,
        }

        property = PropertySampler(
            property_name=property_name,
            property_key=property_key,
            property_value=property_value,
        ).sample()

        await controller.configure(
            device_id=device.mqtt.port,
            module_id=module_id,
            property_info=property,
        )

        mocked_configure.assert_awaited_once_with(
            module_id, property_name, json.dumps(property_content)
        )


@pytest.mark.trio
async def test_configure_wrong_device() -> None:
    device = DeviceConnectionSampler().sample()
    configuration = GlobalConfigurationSampler(num_of_devices=1).sample()

    with ConfigMocker.mock_configuration(configuration) as config:
        service = mocked_device_services()
        service.add_device_to_internals(device)
        service.states[device.mqtt.port].mqtt_client = AsyncMock()
        mocked_configure = AsyncMock()
        service.states[device.mqtt.port].mqtt_client.configure = mocked_configure

        controller = DevicesController(config, service)

        module_id = "module_id_1"

        property = PropertySampler().sample()

        with pytest.raises(Exception):
            await controller.configure(
                device_id=device.mqtt.port + 1,
                module_id=module_id,
                property_info=property,
            )


@pytest.mark.trio
async def test_configure_system() -> None:
    device = DeviceConnectionSampler().sample()
    configuration = GlobalConfigurationSampler(num_of_devices=1).sample()

    with ConfigMocker.mock_configuration(configuration) as config:
        service = mocked_device_services()
        service.add_device_to_internals(device)
        service.states[device.mqtt.port].mqtt_client = AsyncMock()
        mocked_configure = AsyncMock()
        service.states[device.mqtt.port].mqtt_client.configure = mocked_configure

        controller = DevicesController(config, service)

        module_id = "$system"
        property_name = "property_name_1"
        property_key = "property_key_1"
        property_value = "property_value_1"

        property_content = {property_key: property_value}

        property = PropertySampler(
            property_name=property_name,
            property_key=property_key,
            property_value=property_value,
        ).sample()

        await controller.configure(
            device_id=device.mqtt.port,
            module_id=module_id,
            property_info=property,
        )

        mocked_configure.assert_awaited_once_with(
            "backdoor-EA_Main", property_name, json.dumps(property_content)
        )


def _encodeId(device_port: int) -> str:
    return base64.b64encode(str(device_port).encode("utf-8")).decode("utf-8")
