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
from local_console.core.camera.states.accepting_files import AcceptingFilesMixin
from local_console.core.camera.states.base import BaseStateProperties
from local_console.core.camera.states.v2.common import ConnectedCameraStateV2
from local_console.core.camera.v2.components.edge_app import APP_CONFIG_KEY
from local_console.core.camera.v2.components.edge_app import EdgeAppPortSettings
from local_console.core.camera.v2.components.edge_app import EdgeAppSpec
from local_console.core.camera.v2.components.edge_app import UploadMethod
from local_console.core.camera.v2.components.edge_app import UploadSpec
from pydantic import BaseModel
from pydantic import ValidationError

logger = logging.getLogger(__name__)


EXT_IMAGES = "jpg"
EXT_INFERS = "txt"


class StreamingCameraV2(ConnectedCameraStateV2, AcceptingFilesMixin):

    def __init__(
        self,
        base: BaseStateProperties,
        module_id: str,
        config_obj: EdgeAppSpec,
    ) -> None:
        super().__init__(base)
        assert config_obj.common_settings and config_obj.common_settings.process_state
        self._module = module_id
        self._config = config_obj

    async def enter(self, nursery: trio.Nursery) -> None:
        await super().enter(nursery)
        self.files_preamble()

        # Configure global webserver for pushing files to this camera
        upload_url = self._file_inbox.set_file_incoming_callable(
            self._id, self._process_camera_upload
        )
        # simplest logic: blindly set all kinds of uploads as enabled
        upload_spec = UploadSpec(
            enabled=True,
            method=UploadMethod.HTTP_STORAGE,
            endpoint=upload_url,
            path=None,
            storage_name=None,
        )
        port_cfg = EdgeAppPortSettings(
            input_tensor=upload_spec.model_copy(),
            metadata=upload_spec,
        )
        assert port_cfg.input_tensor
        assert port_cfg.metadata
        port_cfg.input_tensor.path = "images"
        port_cfg.metadata.path = "inferences"

        assert self._config.common_settings
        self._config.common_settings.port_settings = port_cfg
        await super().send_configuration(self._module, APP_CONFIG_KEY, self._config)

    async def exit(self) -> None:
        await super().exit()
        self._file_inbox.reset_file_incoming_callable(self._id)

    async def send_configuration(
        self, module_id: str, property_name: str, data: dict[str, Any] | BaseModel
    ) -> None:
        should_stop = False

        if property_name == APP_CONFIG_KEY:
            # This is potentially a payload to get streaming stopped
            try:
                ea_config = EdgeAppSpec.model_validate(data)
                data = ea_config  # so that send_configuration() below can model_dump_json() it.
                cs = ea_config.common_settings
                if (
                    cs
                    and cs.port_settings
                    and cs.port_settings.metadata
                    and cs.port_settings.input_tensor
                    and not cs.port_settings.metadata.enabled
                    and not cs.port_settings.input_tensor.enabled
                ):
                    # it is, so do the state transition
                    should_stop = True

                    if module_id != self._module:
                        logger.warning(
                            f"Stopped has been specified for module "
                            f"{module_id}, but streaming was initiated for module {self._module}"
                        )

            except ValidationError:
                pass

        await super().send_configuration(module_id, property_name, data)
        if should_stop:
            await self._back_to_ready()

    async def _process_camera_upload(self, data: bytes, url_path: str) -> None:
        incoming_file = PurePosixPath(url_path)
        name = incoming_file.name
        extension = incoming_file.suffix.lstrip(".")

        if extension == EXT_INFERS:
            target_dir = self.inference_dir
            assert target_dir
            await self._save_into_input_directory(name, data, target_dir)
        elif extension == EXT_IMAGES:
            target_dir = self.image_dir
            assert target_dir
            await self._save_into_input_directory(name, data, target_dir)
        else:
            logger.warning(f"Unknown incoming file: {incoming_file}")

    async def _back_to_ready(self) -> None:
        from local_console.core.camera.states.v2.ready import ReadyCameraV2

        await self._transit_to(ReadyCameraV2(self._state_properties))
