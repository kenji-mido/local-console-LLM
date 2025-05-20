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
from pathlib import Path
from typing import Protocol

import trio
from local_console.core.camera.streaming import base_dir_for
from local_console.core.camera.streaming import image_dir_for
from local_console.core.camera.streaming import inference_dir_for
from local_console.core.config import Config
from local_console.core.notifications import Notification
from local_console.core.schemas.schemas import DeviceID
from local_console.core.schemas.utils import setup_device_dir_path
from local_console.utils.fstools import check_and_create_directory
from local_console.utils.fstools import StorageSizeWatcher
from trio import MemorySendChannel
from trio.lowlevel import TrioToken

logger = logging.getLogger(__name__)


class AcceptingFilesMixin(Protocol):
    """
    Provides common logic for typed states which deal with files
    coming in from the camera, in order to respect concerns such
    as storage usage quota.

    It is meant to be mixed into full state implementations, with
    the `files_preamble` method called from their `enter()` method.
    Also, state implementations must specialize `_back_to_ready`
    """

    @property
    def _id(self) -> DeviceID: ...

    @property
    def _trio_token(self) -> TrioToken: ...

    @property
    def _message_send_channel(self) -> MemorySendChannel: ...

    @property
    def _dirs_watcher(self) -> StorageSizeWatcher: ...

    def files_preamble(self) -> None:
        if not self.base_dir:
            setup_device_dir_path(self._id)
        self._ensure_directories()

    @property
    def base_dir(self) -> Path | None:
        return base_dir_for(self._id)

    @property
    def image_dir(self) -> Path | None:
        return image_dir_for(self._id)

    @property
    def inference_dir(self) -> Path | None:
        return inference_dir_for(self._id)

    def _ensure_directories(self) -> None:
        image_dir = self.image_dir
        assert image_dir
        inference_dir = self.inference_dir
        assert inference_dir

        if not image_dir.is_dir():
            image_dir.mkdir(parents=True, exist_ok=True)

        if not inference_dir.is_dir():
            inference_dir.mkdir(parents=True, exist_ok=True)

    async def _save_into_input_directory(
        self, file_name: str, content: bytes, target_dir: Path
    ) -> Path | None:
        auto_delete = Config().get_persistent_attr(self._id, "auto_deletion")

        if not auto_delete and not self._dirs_watcher.can_accept():
            await self.on_full(file_name, len(content))
            logger.warning(
                f"Cannot accept file {file_name} as it exceeds storage usage limit"
            )
            return None

        final = target_dir / file_name
        check_and_create_directory(final.parent)
        final.write_bytes(content)
        self._dirs_watcher.incoming(final, auto_delete)

        return final

    async def on_full(self, file_name: str, size: int) -> None:
        base_dir = self.base_dir
        assert base_dir

        try:
            await self._message_send_channel.send(
                Notification(
                    kind="storage-limit-hit",
                    data={
                        "device_id": self._id,
                        "path": base_dir,
                        "quota": self._dirs_watcher.current_limit,
                    },
                )
            )
        except trio.BrokenResourceError:
            # This may happen when shutting down the program.
            # It is not relevant.
            pass

        # Need to transit back to the ready-idle state
        await self._back_to_ready()

    async def _back_to_ready(self) -> None:
        """
        This needs to be implemented per use-case
        """
