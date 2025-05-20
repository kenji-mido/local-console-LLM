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
import pytest
from httpx import AsyncClient
from local_console.core.camera.machine import Camera
from local_console.core.camera.states.v1.common import ConnectedCameraStateV1
from local_console.core.config import Config
from local_console.core.device_services import DeviceServices
from local_console.core.schemas.schemas import GlobalConfiguration
from local_console.fastapi.main import lifespan
from local_console.utils.trio import EVENT_WAITING

from tests.fixtures.devices import stored_devices
from tests.mocks.mock_paho_mqtt import MockMqttAgent
from tests.strategies.samplers.device_config import DeviceConfigurationSampler
from tests.strategies.samplers.mqtt_message import MockMQTTMessage
from tests.strategies.samplers.qr import QRInfoSampler


@pytest.mark.trio
async def test_show_info_from_qr_if_no_handshake_is_made(
    fa_client_with_agent: AsyncClient,
    mocked_agent_fixture: MockMqttAgent,
    single_device_config: GlobalConfiguration,
) -> None:
    device_service: DeviceServices = (
        fa_client_with_agent._transport.app.state.device_service
    )
    device = single_device_config.devices[0]
    device.qr = QRInfoSampler().sample()
    async with stored_devices(single_device_config.devices, device_service):
        result = await fa_client_with_agent.get("/devices")

        assert (
            result.json()["devices"][0]["modules"][0]["property"]["state"][
                "wireless_setting"
            ]["sta_mode_setting"]["ssid"]
            == device.qr.wifi_ssid
        )
        assert (
            result.json()["devices"][0]["modules"][0]["property"]["state"][
                "wireless_setting"
            ]["sta_mode_setting"]["password"]
            == device.qr.wifi_pass
        )
        mocked_agent_fixture.stop_receiving_messages()


@pytest.mark.trio
async def test_consolidate_qr_on_device_handshake(
    fa_client_async: AsyncClient,
    mocked_agent_fixture: MockMqttAgent,
    single_device_config: GlobalConfiguration,
) -> None:
    device_conf = single_device_config.devices[0]
    agent = mocked_agent_fixture
    device_port = device_conf.mqtt.port
    device_id = device_conf.id

    app = fa_client_async._transport.app
    device_service = app.state.device_service
    # The lifespan initializes the device specified in the config
    async with lifespan(app):
        camera: Camera = device_service.get_camera(device_id)
        await camera._transition_to_state(
            ConnectedCameraStateV1(camera._common_properties)
        )

        # When we first get information from the devices,
        # there is no QR information as has never been stored.
        result = await fa_client_async.get("/devices")
        assert (
            result.json()["devices"][0]["modules"][0]["property"]["state"][
                "wireless_setting"
            ]["sta_mode_setting"]["ssid"]
            is None
        )

        device_config = DeviceConfigurationSampler().sample()
        device_config.Network.ProxyPort = device_port
        result = await fa_client_async.get(
            "/provisioning/qrcode",
            params={
                "mqtt_host": device_config.Network.ProxyURL,
                "mqtt_port": device_config.Network.ProxyPort,
                "ntp": device_config.Network.NTP,
                "ip_address": device_config.Network.IPAddress,
                "subnet_mask": device_config.Network.SubnetMask,
                "gateway": device_config.Network.Gateway,
                "dns": device_config.Network.DNS,
                "wifi_ssid": "WIFI-NAME",
                "wifi_pass": "I can not tell you",
            },
        )

        # QR is in memory but still not consolidated
        result = await fa_client_async.get("/devices")
        assert (
            result.json()["devices"][0]["modules"][0]["property"]["state"][
                "wireless_setting"
            ]["sta_mode_setting"]["ssid"]
            is None
        )

        async def check(expected: bool):
            assert camera._common_properties.reported.is_empty() != expected

            result = await fa_client_async.get("/devices")
            devices = result.json()["devices"][0]["modules"][0]["property"]["state"][
                "wireless_setting"
            ]["sta_mode_setting"]

            assert (devices["ssid"] == "WIFI-NAME") == expected
            assert (devices["password"] == "I can not tell you") == expected

        await check(False)

        agent.receives(MockMQTTMessage.handshake_response())
        # Let time for message to be received
        await EVENT_WAITING.wait_for(
            lambda: not camera._common_properties.reported.is_empty()
        )

        await check(True)


@pytest.mark.trio
async def test_do_not_update_host_without_handshake(
    fa_client_async: AsyncClient,
    mocked_agent_fixture: MockMqttAgent,
    single_device_config: GlobalConfiguration,
) -> None:
    device_conf = single_device_config.devices[0]
    device_port = device_conf.mqtt.port
    device_id = device_conf.id
    config_obj = Config()

    app = fa_client_async._transport.app
    async with lifespan(app):
        device_config = DeviceConfigurationSampler().sample()

        assert config_obj.get_device_config(device_id).mqtt.host != "1.2.3.4"
        await fa_client_async.get(
            "/provisioning/qrcode",
            params={
                "mqtt_host": "1.2.3.4",
                "mqtt_port": device_port,
                "ntp": device_config.Network.NTP,
                "ip_address": device_config.Network.IPAddress,
                "subnet_mask": device_config.Network.SubnetMask,
                "gateway": device_config.Network.Gateway,
                "dns": device_config.Network.DNS,
                "wifi_ssid": "WIFI-NAME",
                "wifi_pass": "I can not tell you",
            },
        )
        assert config_obj.get_device_config(device_id).mqtt.host != "1.2.3.4"
