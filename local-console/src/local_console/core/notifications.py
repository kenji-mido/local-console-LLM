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
from typing import Any
from typing import Protocol

import trio
from pydantic import BaseModel
from trio import BrokenResourceError
from trio import MemorySendChannel
from trio import RunFinishedError
from trio.lowlevel import TrioToken


class Notification(BaseModel):
    kind: str
    data: Any


class NotificationsEmitter(Protocol):
    """
    This Protocol states that classes onto which this applies,
    will support async operations by having several async-related
    attributes available. Those are to be provided by the class
    implementation onto which this protocol is mixed..
    """

    _message_send_channel: MemorySendChannel[Notification]
    _trio_token: TrioToken

    async def send_message(self, msg: Notification) -> None:
        try:
            # async with self._message_send_channel:
            await self._message_send_channel.send(msg)
        except BrokenResourceError:
            # This happens when shutting down the program.
            # It is not relevant.
            pass

    def send_message_sync(self, msg: Notification) -> None:
        try:
            trio.from_thread.run(
                self.send_message,
                msg,
                trio_token=self._trio_token,
            )
        except RunFinishedError:
            # Trio seems to expect that functions passed to
            # from_thread.run be long-running, and when they
            # finish it raises this exception.
            pass
