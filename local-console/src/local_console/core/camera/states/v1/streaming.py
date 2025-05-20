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
from pathlib import PurePosixPath
from typing import Any

import trio
from local_console.core.camera.enums import StreamStatus
from local_console.core.camera.states.accepting_files import AcceptingFilesMixin
from local_console.core.camera.states.base import BaseStateProperties
from local_console.core.camera.states.base import MQTTEvent
from local_console.core.camera.states.v1.common import ConnectedCameraStateV1
from local_console.core.camera.states.v1.rpc import v1_rpc_response_to_v2
from local_console.core.camera.streaming import PREVIEW_TARGET
from local_console.core.camera.streaming import PreviewBuffer
from local_console.core.commands.rpc_with_response import DirectCommandResponseBody
from local_console.core.config import Config
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes
from local_console.core.schemas.edge_cloud_if_v1 import StartUploadInferenceData

logger = logging.getLogger(__name__)
config_obj = Config()


class StreamingCameraV1(ConnectedCameraStateV1, AcceptingFilesMixin):

    def __init__(
        self,
        base: BaseStateProperties,
        params: dict[str, Any],
        extra: dict[str, Any],
    ) -> None:
        super().__init__(base)

        self.stream_status = StreamStatus.Inactive
        self._params = params
        self._extra = extra

        # Ancillary variables
        self._extension_images = "jpg"
        self._extension_infers = "txt"

        self._preview = PreviewBuffer()

    async def enter(self, nursery: trio.Nursery) -> None:
        await super().enter(nursery)
        self.files_preamble()

        # Configure global webserver for pushing files to this camera
        upload_url = self._file_inbox.set_file_incoming_callable(
            self._id, self._process_camera_upload
        )

        image_dir = "images"
        as_preview = self._extra.get("preview", False)
        if as_preview:
            self._preview.enable()
            image_dir = PREVIEW_TARGET

        body = StartUploadInferenceData(
            StorageName=upload_url,
            StorageSubDirectoryPath=image_dir,
            StorageNameIR=upload_url,
            StorageSubDirectoryPathIR="inferences",
            **self._params,
        )
        await self._push_rpc(
            "backdoor-EA_Main",
            "StartUploadInferenceData",
            body.model_dump(),
            {},
        )

    async def exit(self) -> None:
        await super().exit()
        await self._rpc_stop_streaming()
        self._preview.disable()
        self._file_inbox.reset_file_incoming_callable(self._id)

    async def on_message_received(self, message: MQTTEvent) -> None:
        await super().on_message_received(message)

        #### FIXME maybe react to the status
        if self._props_report.sensor_status is not None:
            self.stream_status = StreamStatus.from_string(
                self._props_report.sensor_status
            )

    async def run_command(
        self,
        module_id: str,
        method: str,
        params: dict[str, Any],
        extra: dict[str, Any],
    ) -> DirectCommandResponseBody:
        if module_id == "$system" and method == "StartUploadInferenceData":
            raise UserException(
                code=ErrorCodes.EXTERNAL_DEVICE_UNEXPECTED_RPC,
                message="Attempted to start streaming again!",
            )
        elif module_id == "$system" and method == "StopUploadInferenceData":
            from local_console.core.camera.states.v1.ready import ReadyCameraV1

            ready_state = ReadyCameraV1(self._state_properties)
            await self._transit_to(ready_state)
            assert self._rpc_response
            return v1_rpc_response_to_v2(module_id, self._rpc_response)

        else:
            await self._push_rpc(module_id, method, params, extra)
            assert self._rpc_response
            return v1_rpc_response_to_v2(module_id, self._rpc_response)

    @property
    def preview_mode(self) -> PreviewBuffer:
        return self._preview

    async def _process_camera_upload(self, data: bytes, url_path: str) -> None:
        incoming_file = PurePosixPath(url_path)
        name = incoming_file.name
        extension = incoming_file.suffix.lstrip(".")

        if incoming_file.parent.name == PREVIEW_TARGET:
            if extension == self._extension_images:
                self._preview.update(data)
            else:
                logger.warning(
                    f"Got non-image payload of size {len(data)} while in preview mode, at {url_path}"
                )

            # In preview mode, do not perform any operations on the file system
            return

        if extension == self._extension_infers:
            target_dir = self.inference_dir
            assert target_dir
            await self._save_into_input_directory(name, data, target_dir)
        elif extension == self._extension_images:
            target_dir = self.image_dir
            assert target_dir
            await self._save_into_input_directory(name, data, target_dir)
        else:
            logger.warning(f"Unknown incoming file: {incoming_file}")

    async def _back_to_ready(self) -> None:

        from local_console.core.camera.states.v1.ready import ReadyCameraV1

        await self._transit_to(ReadyCameraV1(self._state_properties))
