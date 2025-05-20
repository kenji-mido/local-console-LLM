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
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport
from local_console.core.camera.machine import Camera
from local_console.core.notifications import Notification
from local_console.fastapi.main import generate_server
from local_console.fastapi.main import lifespan

from tests.mocks.config import set_configuration
from tests.strategies.samplers.configs import GlobalConfigurationSampler


@pytest.mark.trio
async def test_send_message_basic(
    fa_client_full_init: tuple[AsyncClient, Camera]
) -> None:
    client, camera = fa_client_full_init

    async with (
        client,
        aconnect_ws("/ws/", client) as websocket,
    ):
        msg = Notification(kind="what", data="some-data")
        await camera.send_notification(msg)
        data = await websocket.receive_text()
        assert data == msg.model_dump_json()


@pytest.mark.trio
async def test_send_message_from_multiple_devices() -> None:

    num_devices = 3
    global_config_sample = GlobalConfigurationSampler(
        num_of_devices=num_devices
    ).sample()
    set_configuration(global_config_sample)

    with (
        patch("local_console.fastapi.main.running_background_task"),
        patch("local_console.fastapi.main.stop_background_task"),
    ):
        app = generate_server()
        client = AsyncClient(
            transport=ASGIWebSocketTransport(app), base_url="http://test"
        )

        async with (
            lifespan(app),
            client,
            aconnect_ws("/ws/", client) as websocket,
        ):
            # Send messages before the websocket client on the
            # other end has a change to read them.
            expected_msgs = []
            for camera in app.state.device_service.get_cameras():
                payload = f"some-test-payload from {camera.id}"
                msg = Notification(kind="what", data=payload)
                expected_msgs.append(msg.model_dump_json())
                await camera.send_notification(msg)

            # The messages must not have melded
            msgs = [await websocket.receive_text() for _ in range(num_devices)]
            assert len(msgs) == num_devices
            assert msgs == expected_msgs

            # and there should be nothing else awaiting
            with pytest.raises(TimeoutError):
                await websocket.receive_text(timeout=0.5)
