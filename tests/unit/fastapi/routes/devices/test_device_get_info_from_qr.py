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
from unittest.mock import patch

import pytest
import trio
from httpx import AsyncClient
from local_console.core.device_services import DeviceServices
from local_console.utils.trio import EVENT_WAITING

from tests.fixtures.agent import mocked_agent_fixture
from tests.fixtures.configs import stored_devices
from tests.fixtures.fastapi import fa_client_with_agent
from tests.mocks.mock_paho_mqtt import MockMqttAgent
from tests.strategies.samplers.configs import DeviceConnectionSampler
from tests.strategies.samplers.device_config import DeviceConfigurationSampler
from tests.strategies.samplers.mqtt_message import MockMQTTMessage
from tests.strategies.samplers.qr import QRInfoSampler


@pytest.mark.trio
async def test_show_info_from_qr_if_no_handshake_is_made(
    fa_client_with_agent: AsyncClient,
    mocked_agent_fixture: MockMqttAgent,
) -> None:
    assert mocked_agent_fixture
    expected_devices = DeviceConnectionSampler().list_of_samples(1)
    device_service: DeviceServices = (
        fa_client_with_agent._transport.app.state.device_service
    )
    device = expected_devices[0]
    device.qr = QRInfoSampler().sample()
    with stored_devices(expected_devices, device_service):
        async with trio.open_nursery() as nursery:
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

            nursery.cancel_scope.cancel()


@pytest.mark.trio
async def test_consolidate_qr_on_device_handshake(
    fa_client_with_agent: AsyncClient,
    mocked_agent_fixture: MockMqttAgent,
) -> None:
    expected_devices = DeviceConnectionSampler().list_of_samples(1)
    device_service: DeviceServices = (
        fa_client_with_agent._transport.app.state.device_service
    )
    device_port = expected_devices[0].mqtt.port
    with stored_devices(expected_devices, device_service):
        async with trio.open_nursery() as nursery:
            agent = mocked_agent_fixture
            agent.wait_for_messages = True
            camera_state = device_service.states[device_port]
            # When we first get information from the devices there is no QR information as has never been stored.
            result = await fa_client_with_agent.get("/devices")

            assert (
                result.json()["devices"][0]["modules"][0]["property"]["state"][
                    "wireless_setting"
                ]["sta_mode_setting"]["ssid"]
                is None
            )

            device_config = DeviceConfigurationSampler().sample()

            device_config.Network.ProxyPort = device_port
            result = await fa_client_with_agent.get(
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
            result = await fa_client_with_agent.get("/devices")

            assert (
                result.json()["devices"][0]["modules"][0]["property"]["state"][
                    "wireless_setting"
                ]["sta_mode_setting"]["ssid"]
                is None
            )

            agent.send_messages([MockMQTTMessage.handshake_response()])

            await EVENT_WAITING.wait_for(
                lambda: camera_state.device_config.value is not None
            )

            assert camera_state.device_config.value is not None

            # QR is consolidated and therefore must see the SSID
            result = await fa_client_with_agent.get("/devices")

            assert (
                result.json()["devices"][0]["modules"][0]["property"]["state"][
                    "wireless_setting"
                ]["sta_mode_setting"]["ssid"]
                == "WIFI-NAME"
            )
            assert (
                result.json()["devices"][0]["modules"][0]["property"]["state"][
                    "wireless_setting"
                ]["sta_mode_setting"]["password"]
                == "I can not tell you"
            )

            nursery.cancel_scope.cancel()


@pytest.mark.trio
@patch(
    "local_console.utils.local_network.get_my_ip_by_routing",
    MagicMock(return_value="192.168.42.42"),
)
async def test_update_host_on_qr_successfully(
    fa_client_with_agent: AsyncClient,
    mocked_agent_fixture: MockMqttAgent,
) -> None:
    expected_devices = DeviceConnectionSampler().list_of_samples(1)
    device_service: DeviceServices = (
        fa_client_with_agent._transport.app.state.device_service
    )
    device_port = expected_devices[0].mqtt.port
    with stored_devices(expected_devices, device_service):
        from local_console.core.config import config_obj

        mqtt_host = config_obj.get_device_config(device_port).mqtt.host

        agent = mocked_agent_fixture
        agent.wait_for_messages = True
        device_config = DeviceConfigurationSampler().sample()
        # When we send a QR
        await fa_client_with_agent.get(
            "/provisioning/qrcode",
            params={
                "mqtt_host": "localhost",
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
        # And device handshake it
        agent.send_messages([MockMQTTMessage.handshake_response()])

        # config does not update configured mqtt host
        await EVENT_WAITING.wait_for(lambda: False)
        assert config_obj.get_device_config(device_port).mqtt.host == mqtt_host


@pytest.mark.trio
async def test_do_not_update_host_without_handshake(
    fa_client_with_agent: AsyncClient,
    mocked_agent_fixture: MockMqttAgent,
) -> None:
    expected_devices = DeviceConnectionSampler().list_of_samples(1)
    device_service: DeviceServices = (
        fa_client_with_agent._transport.app.state.device_service
    )
    device_port = expected_devices[0].mqtt.port
    with stored_devices(expected_devices, device_service):
        from local_console.core.config import config_obj

        agent = mocked_agent_fixture
        agent.wait_for_messages = True
        device_config = DeviceConfigurationSampler().sample()
        # When we send a QR
        assert config_obj.get_device_config(device_port).mqtt.host != "1.2.3.4"
        await fa_client_with_agent.get(
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
        assert config_obj.get_device_config(device_port).mqtt.host != "1.2.3.4"


@pytest.mark.trio
async def test_handshake_changes_do_not_update_config(
    fa_client_with_agent: AsyncClient,
    mocked_agent_fixture: MockMqttAgent,
) -> None:
    expected_devices = DeviceConnectionSampler().list_of_samples(1)
    device_service: DeviceServices = (
        fa_client_with_agent._transport.app.state.device_service
    )
    device_port = expected_devices[0].mqtt.port
    qr_info = QRInfoSampler().sample()
    qr_info.ntp = "4.3.2.1"
    with stored_devices(expected_devices, device_service):
        from local_console.core.config import config_obj

        agent = mocked_agent_fixture
        state = device_service.states[device_port]
        assert state.device_config.value is None
        agent.wait_for_messages = True
        device = config_obj.get_device_config(device_port)
        device.qr = qr_info
        config_obj.save_config()
        msg = MockMQTTMessage.handshake_response()
        assert isinstance(msg.payload, bytes)
        assert qr_info.ntp not in msg.payload.decode("utf-8")
        # And device handshake it
        agent.send_messages([msg])

        # config get update with the host ip
        await EVENT_WAITING.wait_for(lambda: state.device_config.value is not None)
        assert config_obj.get_device_config(device_port).qr.ntp == "4.3.2.1"
        agent.wait_for_messages = False
