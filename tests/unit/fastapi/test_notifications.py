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
from fastapi import FastAPI
from fastapi import WebSocket
from httpx import AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport
from local_console.core.notifications import Notification
from local_console.fastapi.dependencies.notifications import messages_channel
from local_console.fastapi.dependencies.notifications import WebSocketManager


@pytest.mark.trio
async def test_basic_websockets_framework():
    app = FastAPI()

    @app.get("/")
    async def read_main():
        return {"msg": "Hello World"}

    @app.websocket("/ws")
    async def websocket_handler(websocket: WebSocket):
        await websocket.accept()

        # test client->server
        await websocket.send_json({"msg": "Hello WebSocket"})

        # test server->client
        reply = await websocket.receive_text()
        assert reply == "pongback"

        await websocket.close()

    async with AsyncClient(
        transport=ASGIWebSocketTransport(app), base_url="http://test"
    ) as client:
        http_response = await client.get("/")
        assert http_response.status_code == 200

        async with aconnect_ws("/ws", client) as ws:
            # test client->server
            data = await ws.receive_json()
            assert data == {"msg": "Hello WebSocket"}

            # test server->client
            await ws.send_text("pongback")


@pytest.fixture
async def infrastructure(nursery):
    """
    Provide a FastAPI instance with a websocket handler, along with
    an async, websocket-ready test object
    """

    async with messages_channel(nursery) as (sender, receiver):
        ws_man = WebSocketManager(nursery, receiver.clone())

        app = FastAPI()

        @app.websocket("/ws")
        async def websocket(websocket: WebSocket):
            await ws_man.loop_for(websocket)

        yield sender.clone(), AsyncClient(
            transport=ASGIWebSocketTransport(app), base_url="http://test"
        )


@pytest.mark.trio
async def test_core_notification_mechanism(infrastructure):
    sender, test_client = infrastructure

    async with (
        test_client,
        sender,
        aconnect_ws("/ws", test_client) as websocket,
    ):
        msg = Notification(kind="data", data="some message")

        # Send something over the memory channel...
        await sender.send(msg)

        # ... and receive it over the websocket
        data = await websocket.receive_text()
        assert data == msg.model_dump_json()
