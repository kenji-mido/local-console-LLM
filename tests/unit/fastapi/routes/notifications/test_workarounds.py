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
"""
This test submodule illustrates limitations of the FastAPI + websockets +
Starlette + httpx + httpx-ws stack. See:

https://github.com/fastapi/fastapi/issues/98
"""
import pytest
from fastapi import APIRouter
from fastapi import FastAPI
from fastapi import WebSocket
from httpx import AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport


@pytest.mark.trio
async def test_routing_shenanigan_works():
    """
    Notice how the prefix for a router for a websocket path cannot be
    defined the same way the prefix for HTTP routes can:

    This test works, with the prefix specified to `app.include_router()`,
    instead of when the router is created with `APIRouter()`
    """

    prefix_router = APIRouter()
    app = FastAPI()

    @app.websocket_route("/")
    async def index(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_text("Hello, world!")
        await websocket.close()

    @prefix_router.websocket_route("/")
    async def routerprefixindex(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_text("Hello, router with prefix!")
        await websocket.close()

    app.include_router(prefix_router, prefix="/prefix")

    async with (
        AsyncClient(
            transport=ASGIWebSocketTransport(app), base_url="http://test"
        ) as client,
        aconnect_ws("/prefix/", client) as websocket,
    ):
        data = await websocket.receive_text()
        assert data == "Hello, router with prefix!"


@pytest.mark.trio
async def test_routing_shenanigan_fails():
    """
    Notice how the prefix for a router for a websocket path cannot be
    defined the same way the prefix for HTTP routes can:

    This test shows the failure when the prefix specified to `APIRouter()
    when the router is created, instead of when the call to
    `app.include_router()` is made
    """

    app = FastAPI()
    prefix_router = APIRouter(prefix="/prefix")

    @app.websocket_route("/")
    async def index(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_text("Hello, world!")
        await websocket.close()

    @prefix_router.websocket_route("/")
    async def routerprefixindex(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_text("Hello, router with prefix!")
        await websocket.close()

    app.include_router(prefix_router)

    async with (
        AsyncClient(
            transport=ASGIWebSocketTransport(app), base_url="http://test"
        ) as client,
    ):
        with pytest.raises(BaseException):
            async with aconnect_ws("/prefix/", client):
                """
                Although the exception here is caused by an assert in httpx-ws,
                it should instead make FastAPI return a 40x error, which is what
                is observed when testing the server with a third-party client, such
                as a browser's websocket object, or websocat.
                """
                pass
