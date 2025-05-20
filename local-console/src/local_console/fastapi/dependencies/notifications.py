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
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated
from typing import Any

from fastapi import Depends
from fastapi import FastAPI
from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from trio import CancelScope
from trio import MemoryReceiveChannel
from trio import MemorySendChannel
from trio import Nursery
from trio import open_memory_channel
from trio import TASK_STATUS_IGNORED

logger = logging.getLogger(__name__)


@asynccontextmanager
async def messages_channel(
    nursery: Nursery,
) -> AsyncGenerator[tuple[MemorySendChannel, MemoryReceiveChannel], None]:
    """
    Trio's memory channels are the coupling mechanism that enables
    implementing notifications over websockets while maintaining
    the core camera logic agnostic with respect to this aspect.
    """
    channels: tuple[MemorySendChannel, MemoryReceiveChannel] = open_memory_channel(0)
    sender_ch, receiver_ch = channels
    yield sender_ch, receiver_ch


class WebSocketManager:
    def __init__(self, nursery: Nursery, receiver_channel: MemoryReceiveChannel):
        self._nursery = nursery
        self._recv_channel = receiver_channel

        self.active_connections: list[WebSocket] = []

    async def loop_for(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

        # Launch message listener in the background.
        # About using .clone() below, see:
        # https://trio.readthedocs.io/en/stable/reference-core.html#managing-multiple-producers-and-or-multiple-consumers
        cancel_scope = await self._nursery.start(
            self._push_from_channel, websocket, self._recv_channel.clone()
        )
        # Maintain connection alive, cancelling the listener upon disconnect
        try:
            while True:
                await websocket.receive_bytes()
        except WebSocketDisconnect:
            self.disconnect(websocket)
        finally:
            # Cause the receive channel listener task to finish
            cancel_scope.cancel()

    async def _push_from_channel(
        self,
        websocket: WebSocket,
        receiver: MemoryReceiveChannel,
        *,
        task_status: Any = TASK_STATUS_IGNORED,
    ) -> None:
        with CancelScope() as scope:
            # Stand ready for this task to be finished upon websocket termination
            task_status.started(scope)

            async with receiver:
                async for message in receiver:
                    logger.debug(f"Notifying over websocket: {message}")
                    await websocket.send_text(message.model_dump_json())

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.remove(websocket)


def add_websockets(
    app: FastAPI, nursery: Nursery, receiver_channel: MemoryReceiveChannel
) -> None:
    if not hasattr(app.state, "websockets"):
        app.state.websockets = WebSocketManager(nursery, receiver_channel)


def websockets_from_app(app: FastAPI) -> WebSocketManager:
    assert isinstance(app.state.websockets, WebSocketManager)
    return app.state.websockets


InjectWebSocketManager = Annotated[WebSocketManager, Depends(websockets_from_app)]
