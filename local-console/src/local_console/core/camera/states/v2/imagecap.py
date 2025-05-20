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
from base64 import b64decode
from typing import Any

import trio
from local_console.core.camera.states.accepting_files import AcceptingFilesMixin
from local_console.core.camera.states.base import BaseStateProperties
from local_console.core.camera.states.v2.common import ConnectedCameraStateV2
from local_console.core.camera.streaming import PreviewBuffer
from local_console.core.camera.v2.components.direct_get_image import (
    DirectGetImageParameters,
)
from local_console.core.camera.v2.components.direct_get_image import (
    DirectGetImageResponse,
)
from local_console.core.commands.rpc_with_response import DirectCommandResponse
from local_console.utils.timing import as_timestamp
from local_console.utils.timing import now

logger = logging.getLogger(__name__)

MODULE = "$system"
COMMAND = "direct_get_image"


class ImageCapturingCameraV2(ConnectedCameraStateV2, AcceptingFilesMixin):

    def __init__(
        self,
        base: BaseStateProperties,
        params: dict[str, Any],
        extra: dict[str, Any],
    ) -> None:
        super().__init__(base)

        self._params = params
        self._extra = extra
        self._preview = PreviewBuffer()

    @property
    def in_preview_mode(self) -> bool:
        preview = bool(self._extra.get("preview", False))
        return preview

    @property
    def preview_mode(self) -> PreviewBuffer:
        return self._preview

    async def enter(self, nursery: trio.Nursery) -> None:
        await super().enter(nursery)
        self.files_preamble()

        if self.in_preview_mode:
            self._preview.enable()

        result = await self._get_frame(self._params)
        self._rpc_response = result

    async def exit(self) -> None:
        await super().exit()
        self._preview.disable()

    async def run_command(
        self,
        module_id: str,
        method: str,
        params: dict[str, Any],
        extra: dict[str, Any],
    ) -> DirectCommandResponse:
        if module_id == MODULE and method == COMMAND:
            should_stop = extra.get("stop", False)
            if not should_stop:
                return await self._get_frame(params)
            else:
                await self._back_to_ready()
                return DirectCommandResponse.empty_ok()
        else:
            return await super().run_command(module_id, method, params, extra)

    async def _get_frame(self, raw_params: dict[str, Any]) -> DirectCommandResponse:
        params = DirectGetImageParameters.model_validate(raw_params)
        result = await super().run_command(MODULE, COMMAND, params.model_dump(), {})

        image_response = DirectGetImageResponse.model_validate_json(
            result.direct_command_response.response
        )
        data = b64decode(image_response.image.encode())

        if self.in_preview_mode:
            self._preview.update(data)
        else:
            image_dir = self.image_dir
            assert image_dir

            target_filename = as_timestamp(now()) + ".jpg"
            await self._save_into_input_directory(target_filename, data, image_dir)

        return result

    async def _back_to_ready(self) -> None:
        from local_console.core.camera.states.v2.ready import ReadyCameraV2

        await self._transit_to(ReadyCameraV2(self._state_properties))
