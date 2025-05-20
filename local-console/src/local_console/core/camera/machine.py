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
from typing import Any
from typing import Callable
from typing import Optional

import trio
from local_console.core.camera.enums import ConnectionState
from local_console.core.camera.firmware import FirmwareInfo
from local_console.core.camera.schemas import PropertiesReport
from local_console.core.camera.state_guard import only_in_states
from local_console.core.camera.states.base import BaseStateProperties
from local_console.core.camera.states.base import MQTTDriver
from local_console.core.camera.states.base import State
from local_console.core.camera.states.base import StateWithProperties
from local_console.core.camera.states.base import Uninitialized
from local_console.core.camera.states.common import DisconnectedCamera
from local_console.core.camera.states.common import IdentifyingCamera
from local_console.core.camera.states.v1.common import ConnectedCameraStateV1
from local_console.core.camera.states.v1.deployment import ClearingAppCameraV1
from local_console.core.camera.states.v1.deployment import DeployingAppCameraV1
from local_console.core.camera.states.v1.ready import ReadyCameraV1
from local_console.core.camera.states.v1.streaming import StreamingCameraV1
from local_console.core.camera.states.v2.common import ConnectedCameraStateV2
from local_console.core.camera.states.v2.deployment import ClearingAppCameraV2
from local_console.core.camera.states.v2.deployment import DeployingAppCameraV2
from local_console.core.camera.states.v2.imagecap import ImageCapturingCameraV2
from local_console.core.camera.states.v2.ready import ReadyCameraV2
from local_console.core.camera.streaming import PreviewBuffer
from local_console.core.commands.deploy import DeploymentSpec
from local_console.core.commands.deploy import StageNotifyFn
from local_console.core.commands.rpc_with_response import DirectCommandResponse
from local_console.core.config import Config
from local_console.core.enums import DEFAULT_PERSIST_SETTINGS
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes
from local_console.core.notifications import Notification
from local_console.core.schemas.schemas import DeviceConnection
from local_console.core.schemas.schemas import DeviceID
from local_console.core.schemas.schemas import DeviceType
from local_console.core.schemas.schemas import Persist
from local_console.core.schemas.utils import setup_device_dir_path
from local_console.servers.webserver import AsyncWebserver
from local_console.servers.webserver import FileInbox
from local_console.utils.fstools import StorageSizeWatcher
from trio import BrokenResourceError
from trio import MemorySendChannel
from trio import RunFinishedError
from trio import TASK_STATUS_IGNORED
from trio.lowlevel import TrioToken


logger = logging.getLogger(__name__)


class Camera:
    """
    Comprises the FSM that tracks a camera's execution state,
    plus all required infrastructure required to excite the FSM
    to keep it up to date. Also provides methods that are used
    by other objects in the software (the public interface).
    """

    ### Public interface ###

    def __init__(
        self,
        config: DeviceConnection,
        message_send_channel: MemorySendChannel,
        webserver: AsyncWebserver,
        file_inbox: FileInbox,
        trio_token: TrioToken,
        on_report_received: Callable[[DeviceID, PropertiesReport], None],
    ) -> None:
        self._common_properties = BaseStateProperties(
            id=config.id,
            mqtt_drv=MQTTDriver(config),
            webserver=webserver,
            file_inbox=file_inbox,
            transition_fn=self._transition_to_state,
            trio_token=trio_token,
            message_send_channel=message_send_channel,
            dirs_watcher=StorageSizeWatcher(
                DEFAULT_PERSIST_SETTINGS.model_copy(),
                on_delete_cb=self._notify_directory_deleted,
            ),
            device_type=DeviceType.UNKNOWN,
            reported=PropertiesReport(),
            on_report_fn=on_report_received,
        )
        self._nursery: Optional[trio.Nursery] = None
        self._cancel_scope: Optional[trio.CancelScope] = None
        self._started = trio.Event()
        self._should_exit = trio.Event()

        self._state: StateWithProperties = Uninitialized.new()
        self._setup_dirs_watch(config)

    @property
    def id(self) -> DeviceID:
        return self._common_properties.id

    @property
    def current_state(self) -> type[State] | None:
        return type(self._state) if self._state else None

    @property
    def device_type(self) -> DeviceType:
        return self._common_properties.device_type

    @property
    def connection_status(self) -> ConnectionState:
        if self.current_state in [Uninitialized, DisconnectedCamera]:
            return ConnectionState.DISCONNECTED
        elif self.current_state is IdentifyingCamera:
            return ConnectionState.CONNECTING
        else:
            return ConnectionState.CONNECTED

    @only_in_states([ReadyCameraV1, ReadyCameraV2])
    async def start_app_deployment(
        self,
        target_spec: DeploymentSpec,
        event_flag: trio.Event,
        error_notify: Callable[[str], None],
        stage_notify_fn: StageNotifyFn | None = None,
        timeout_secs: int = 30,
    ) -> None:
        assert hasattr(
            self._state, "start_app_deployment"
        )  # mypy does not infer type narrowing due to the decorator
        # Use deep copy to avoid later deployments modify the reference
        self._common_properties.reported.latest_deployment_spec = target_spec
        await self._state.start_app_deployment(
            target_spec, event_flag, error_notify, stage_notify_fn, timeout_secs
        )

    @only_in_states(
        [
            ClearingAppCameraV1,
            DeployingAppCameraV1,
            ClearingAppCameraV2,
            DeployingAppCameraV2,
        ]
    )
    async def stop_app_deployment(self) -> None:
        assert hasattr(
            self._state, "stop_deployment"
        )  # mypy does not infer type narrowing due to the decorator
        await self._state.stop_deployment()

    @only_in_states([ConnectedCameraStateV1, ConnectedCameraStateV2])
    async def send_configuration(
        self, module_id: str, property_name: str, data: dict[str, Any]
    ) -> None:
        assert hasattr(
            self._state, "send_configuration"
        )  # mypy does not infer type narrowing based on the decorator
        logger.debug(f"Caching configuration {property_name}: {data}")
        self._common_properties.reported.latest_edge_app_config = data
        await self._state.send_configuration(module_id, property_name, data)

    @only_in_states([ConnectedCameraStateV1, ConnectedCameraStateV2])
    async def run_command(
        self,
        module_id: str,
        method: str,
        params: dict[str, Any],
        extra: dict[str, Any],
    ) -> DirectCommandResponse | None:
        assert hasattr(
            self._state, "run_command"
        )  # mypy does not infer type narrowing based on the decorator
        res: DirectCommandResponse | None = await self._state.run_command(
            module_id, method, params, extra
        )
        return res

    @property
    @only_in_states([StreamingCameraV1, ImageCapturingCameraV2])
    def preview_mode(self) -> PreviewBuffer:
        assert hasattr(self._state, "preview_mode") and isinstance(
            self._state.preview_mode, PreviewBuffer
        )  # mypy does not infer type narrowing based on the decorator
        return self._state.preview_mode

    # TODO add V2
    @only_in_states([ReadyCameraV1])
    async def perform_firmware_update(
        self,
        firmware_info: FirmwareInfo,
        event_flag: trio.Event,
        error_notify: Callable[[str], Any],
        timeout_minutes: int = 4,
        use_configured_port: bool = False,
    ) -> None:
        assert hasattr(
            self._state, "perform_firmware_update"
        )  # mypy does not infer type narrowing based on the decorator
        await self._state.perform_firmware_update(
            firmware_info,
            event_flag,
            error_notify,
            timeout_minutes,
            use_configured_port,
        )

    @only_in_states([ReadyCameraV1, ReadyCameraV2])
    async def deploy_sensor_model(
        self,
        package_file: Path,
        event_flag: trio.Event,
        error_notify: Callable,
        timeout_undeploy_secs: float = 30.0,
        timeout_deploy_secs: float = 90.0,
        use_configured_port: bool = False,
    ) -> None:
        assert hasattr(
            self._state, "deploy_sensor_model"
        )  # mypy does not infer type narrowing based on the decorator
        await self._state.deploy_sensor_model(
            package_file,
            event_flag,
            error_notify,
            timeout_undeploy_secs,
            timeout_deploy_secs,
            use_configured_port,
        )

    async def setup(self, *, task_status: Any = TASK_STATUS_IGNORED) -> None:
        async with trio.open_nursery() as nursery:
            self._nursery = nursery
            self._cancel_scope = nursery.cancel_scope

            # This may raise exceptions
            await nursery.start(self._common_properties.mqtt_drv.setup)
            self._common_properties.dirs_watcher.start()

            # Kickstart the state transitions
            initial_state = DisconnectedCamera(self._common_properties)
            await self._transition_to_state(initial_state)

            task_status.started()
            self._started.set()
            await self._should_exit.wait()

        logger.debug(f"Device with ID '{self.id}' shut down")

    def shutdown(self) -> None:
        self._should_exit.set()
        if self._started.is_set():
            assert self._cancel_scope
            self._common_properties.dirs_watcher.stop()
            self._cancel_scope.cancel()

    def current_storage_usage(self) -> int:
        return self._common_properties.dirs_watcher.size()

    def update_storage_config(self, new_config: Persist) -> None:
        self._common_properties.dirs_watcher.apply(new_config, self.id)

    ### Internal methods ###

    async def _transition_to_state(self, new_state: StateWithProperties) -> None:
        """
        To be called from the current state instance to transition
        to a new state instance.

        Executes the {exit old -> set new -> enter new} sequence
        that's expected of typical FSM implementations.
        """
        assert self._nursery

        if self._state:
            await self._state.exit()

        logger.debug(
            f"Camera moving out of state {(self.current_state or type(None)).__name__} into {type(new_state).__name__}"
        )
        self._state = new_state
        self._common_properties.mqtt_drv.set_handler(self._state.on_message_received)

        await self._state.enter(self._nursery)

    def _setup_dirs_watch(self, config: DeviceConnection) -> None:
        id = config.id
        try:
            desired_folder = config.persist.device_dir_path
            self._common_properties.dirs_watcher.apply(config.persist, id)
        except UserException as e:
            if e.code == ErrorCodes.EXTERNAL_CANNOT_USE_DIRECTORY:
                default_dir_base = setup_device_dir_path(id)
                Config().update_persistent_attr(id, "auto_deletion", False)
                logger.warning(
                    f"No permission for the selected folder: {desired_folder}. "
                    f"Reverting to default: {default_dir_base} with ADF off."
                )
                updated_params = Config().get_device_config(id).persist
                self._common_properties.dirs_watcher.apply(updated_params, id)

    def _notify_directory_deleted(self, dir_path: Path) -> None:
        self.send_notification_sync(
            Notification(
                kind="directory-deleted",
                data={
                    "device_id": self.id,
                    "path": str(dir_path),
                },
            )
        )

    async def send_notification(self, msg: Notification) -> None:
        try:
            await self._common_properties.message_send_channel.send(msg)
        except BrokenResourceError:
            # This happens when shutting down the program.
            # It is not relevant.
            pass

    def send_notification_sync(self, msg: Notification) -> None:
        try:
            trio.from_thread.run(
                self.send_notification,
                msg,
                trio_token=self._common_properties.trio_token,
            )
        except RunFinishedError:
            # Trio seems to expect that functions passed to
            # from_thread.run be long-running, and when they
            # finish running, it raises this exception.
            pass
