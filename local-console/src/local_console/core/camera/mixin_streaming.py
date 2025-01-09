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
import json
import logging
import platform
from datetime import datetime
from datetime import timedelta
from functools import partial
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any
from typing import Callable
from typing import Optional
from typing import Protocol

import trio
from local_console.clients.agent import Agent
from local_console.core.camera._shared import IsAsyncReady
from local_console.core.camera.axis_mapping import pixel_roi_from_normals
from local_console.core.camera.axis_mapping import UnitROI
from local_console.core.camera.enums import ApplicationType
from local_console.core.camera.enums import UnitScale
from local_console.core.camera.flatbuffers import add_class_names
from local_console.core.camera.flatbuffers import flatbuffer_binary_to_json
from local_console.core.camera.flatbuffers import FlatbufferError
from local_console.core.camera.flatbuffers import get_output_from_inference_results
from local_console.core.camera.streaming import FileGrouping
from local_console.core.config import config_obj
from local_console.core.enums import get_default_files_dir
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes
from local_console.core.schemas.edge_cloud_if_v1 import StartUploadInferenceData
from local_console.servers.webserver import AsyncWebserver
from local_console.utils.fstools import check_and_create_directory
from local_console.utils.fstools import DirectoryMonitor
from local_console.utils.fstools import size_unit_to_bytes
from local_console.utils.fstools import StorageSizeWatcher
from local_console.utils.local_network import get_webserver_ip
from local_console.utils.tracking import TrackingVariable
from typing_extensions import Self

logger = logging.getLogger(__name__)


# MQTT constants

EA_STATE_TOPIC = "state/backdoor-EA_Main/placeholder"
SYSINFO_TOPIC = "systemInfo"
DEPLOY_STATUS_TOPIC = "deploymentStatus"
CONNECTION_STATUS_TIMEOUT = timedelta(seconds=180)

# Webserver constants

# Incoming images tend to be under 100 kB.
# Inference files are much smaller in most cases
MAX_INCOMING_SIZE: int = 500 * 1024


class HasMQTTset(Protocol):
    """
    This Protocol states that classes onto which this applies,
    will have a `mqtt_client` member. For StreamingMixin below,
    this means that `mqtt_client` originates elsewhere within
    CameraState, but StreamingMixin expects to find it.
    """

    mqtt_client: Optional[Agent]
    mqtt_port: TrackingVariable[int]


def default_process_camera_upload(
    self: "StreamingMixin", data: bytes, url_path: str
) -> None:
    if hasattr(self, "_last_reception"):
        self._last_reception = datetime.now()

    incoming_file = PurePosixPath(url_path)
    if incoming_file.suffix.lstrip(".") == self._extension_infers:
        assert self.inference_dir_path.value
        target_dir = Path(self.inference_dir_path.value)
        assert target_dir
        stored_file = self._save_into_input_directory(
            incoming_file.name, data, target_dir
        )
        self._grouper.register(stored_file, stored_file)

    elif incoming_file.suffix.lstrip(".") == self._extension_images:
        assert self.image_dir_path.value
        target_dir = Path(self.image_dir_path.value)
        assert target_dir
        stored_file = self._save_into_input_directory(
            incoming_file.name, data, target_dir
        )
        self._grouper.register(stored_file, stored_file)
    else:
        logger.warning(f"Unknown incoming file: {incoming_file}")

    # Process matched image-inference file pairs
    for pair in self._grouper:
        inference_file = pair[self._extension_infers]
        image_file = pair[self._extension_images]

        payload_render = inference_file.read_text()
        output_data = get_output_from_inference_results(inference_file.read_bytes())
        if self.vapp_schema_file.value:
            try:
                output_tensor = self._get_flatbuffers_inference_data(output_data)
                if output_tensor:
                    payload_render = json.dumps(output_tensor, indent=2)
            except FlatbufferError as e:
                logger.error("Error decoding inference data:", exc_info=e)

        self.inference_field.value = payload_render
        self.stream_image.value = str(image_file)


class StreamingMixin(HasMQTTset, IsAsyncReady):
    """
    This Mix-in class covers the concerns of streaming status and control
    belonging to a camera's state. This includes the start/stop commands
    for streaming and inference, and managing the webserver that supports
    the associated data traffic.
    """

    DEFAULT_SIZE = 100
    DEFAULT_UNIT = UnitScale.MB

    def __init__(
        self,
        process_camera_upload: Callable[
            [Self, bytes, str], None
        ] = default_process_camera_upload,
    ) -> None:

        self._process_camera_upload = partial(process_camera_upload, self)
        # Ancillary variables
        self.upload_port: int | None = None
        self._extension_images = "jpg"
        self._extension_infers = "txt"
        self._grouper = FileGrouping({self._extension_images, self._extension_infers})
        self.total_dir_watcher = StorageSizeWatcher(
            size_unit_to_bytes(StreamingMixin.DEFAULT_SIZE, StreamingMixin.DEFAULT_UNIT)
        )
        self.dir_monitor = DirectoryMonitor()

        # State variables
        self.stream_image: TrackingVariable[str] = TrackingVariable("")
        self.image_dir_path: TrackingVariable[Path] = TrackingVariable()
        self.roi: TrackingVariable[UnitROI] = TrackingVariable()

        self.inference_field: TrackingVariable[str] = TrackingVariable("")
        self.inference_dir_path: TrackingVariable[Path] = TrackingVariable()

        self.size: TrackingVariable[int] = TrackingVariable(StreamingMixin.DEFAULT_SIZE)
        self.unit: TrackingVariable[UnitScale] = TrackingVariable(
            StreamingMixin.DEFAULT_UNIT
        )

        self.vapp_schema_file: TrackingVariable[str] = TrackingVariable("")
        self.vapp_config_file: TrackingVariable[str] = TrackingVariable("")
        self.vapp_labels_file: TrackingVariable[str] = TrackingVariable("")
        self.vapp_type: TrackingVariable[ApplicationType] = TrackingVariable()
        self.vapp_labels_map: TrackingVariable[dict[int, str]] = TrackingVariable()

    def _init_bindings_streaming(self) -> None:
        """
        These bindings among variables implement business logic that requires
        no further data than the one contained among the variables.
        """
        self.image_dir_path.subscribe(self.input_directory_setup)
        self.inference_dir_path.subscribe(self.input_directory_setup)
        self.size.subscribe(self.set_storage_limit)
        self.unit.subscribe(self.set_storage_limit)

    async def streaming_rpc_stop(self) -> None:
        assert self.mqtt_client

        instance_id = "backdoor-EA_Main"
        method = "StopUploadInferenceData"
        await self.mqtt_client.rpc(instance_id, method, "{}")

    def streaming_rpc_start_content(
        self, roi: Optional[UnitROI] = None
    ) -> StartUploadInferenceData:

        assert self.mqtt_port.value
        device_conf = config_obj.get_device_config(self.mqtt_port.value)
        host = get_webserver_ip(device_conf)

        upload_url = f"http://{host}:{self.upload_port}"
        (h_offset, v_offset), (h_size, v_size) = pixel_roi_from_normals(roi)
        return StartUploadInferenceData(
            StorageName=upload_url,
            StorageSubDirectoryPath="images",
            StorageNameIR=upload_url,
            StorageSubDirectoryPathIR="inferences",
            CropHOffset=h_offset,
            CropVOffset=v_offset,
            CropHSize=h_size,
            CropVSize=v_size,
        )

    async def streaming_rpc_start(self, roi: Optional[UnitROI] = None) -> None:
        assert self.mqtt_client

        instance_id = "backdoor-EA_Main"
        method = "StartUploadInferenceData"

        await self.mqtt_client.rpc(
            instance_id,
            method,
            self.streaming_rpc_start_content(roi).model_dump_json(),
        )

    async def blobs_webserver_task(self, mqtt_port_as_id: int) -> None:
        """
        Spawn a webserver on an arbitrary available port for
        receiving images from a camera.
        """
        async with AsyncWebserver(
            Path(),
            port=0,
            on_incoming=self._process_camera_upload,
            max_upload_size=MAX_INCOMING_SIZE,
        ) as image_serve:

            assert image_serve.port
            self.upload_port = image_serve.port
            logger.info(f"Webserver listening on port {self.upload_port}")

            default_dir_base = (
                get_default_files_dir() / "local-console" / str(mqtt_port_as_id)
            )
            if not self.image_dir_path.value:
                image_directory = default_dir_base / "images"
                image_directory.mkdir(parents=True, exist_ok=True)
                self.image_dir_path.value = image_directory
            if not self.inference_dir_path.value:
                inference_directory = default_dir_base / "inferences"
                inference_directory.mkdir(parents=True, exist_ok=True)
                self.inference_dir_path.value = inference_directory

            await trio.sleep_forever()

    def input_directory_setup(
        self, current: Optional[str], previous: Optional[str]
    ) -> None:
        cur_path = Path(current) if isinstance(current, str) else current
        pre_path = Path(previous) if isinstance(previous, str) else previous

        if cur_path == pre_path:
            return

        if cur_path:
            check_and_create_directory(cur_path)
            folders_setup_validation(cur_path)
            self.total_dir_watcher.set_path(cur_path)
            self.dir_monitor.watch(cur_path, self.notify_directory_deleted)

        if pre_path:
            self.total_dir_watcher.unwatch_path(pre_path)
            self.dir_monitor.unwatch(pre_path)

        logger.debug(f"Directory '{previous}' has changed to '{current}'")

    def set_storage_limit(self, current: Any, previous: Any) -> None:
        if not self.unit.value or not self.size.value:
            return
        new_size = size_unit_to_bytes(self.size.value, self.unit.value)
        logger.debug(f"Updating size to {new_size}")
        self.total_dir_watcher.set_storage_limit(new_size)

    def notify_directory_deleted(self, dir_path: Path) -> None:
        self.send_message_sync("error", f"Directory {dir_path} does no longer exist.")

    def _save_into_input_directory(
        self, file_name: str, content: bytes, target_dir: Path
    ) -> Path:
        final = target_dir / file_name
        check_and_create_directory(final.parent)
        final.write_bytes(content)
        self.total_dir_watcher.incoming(final)
        return final

    def _get_flatbuffers_inference_data(
        self, flatbuffer_payload: bytes
    ) -> None | str | dict:
        return_value = None
        if self.vapp_schema_file.value:
            json_data = flatbuffer_binary_to_json(
                self.vapp_schema_file.value, flatbuffer_payload
            )
            labels_map = self.vapp_labels_map.value
            if labels_map:
                add_class_names(json_data, labels_map)
            return_value = json_data

        return return_value


def folders_setup_validation(selected_dir: Path) -> None:

    # Cross-platform file write smoke test
    try:
        test_f = selected_dir / "__lctestfile"
        test_f.write_text("1")
        test_f.unlink()
    except Exception as e:
        raise UserException(
            code=ErrorCodes.EXTERNAL_CANNOT_USE_DIRECTORY,
            # FIXME improve this
            message=str(e),
        )

    # On Windows, force users to store files under Documents
    # in order to avoid potential permissions issues
    os_name = platform.system()
    if os_name == "Windows":
        docs_dir = get_default_files_dir()
        if not selected_dir.is_relative_to(docs_dir):
            raise UserException(
                code=ErrorCodes.EXTERNAL_CANNOT_USE_DIRECTORY,
                message="Please select your folders under your main 'Documents' folder",
            )
