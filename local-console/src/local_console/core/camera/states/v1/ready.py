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

import trio
from local_console.core.camera.firmware import FirmwareInfo
from local_console.core.camera.states.base import BaseStateProperties
from local_console.core.camera.states.base import MQTTEvent
from local_console.core.camera.states.v1.common import ConnectedCameraStateV1
from local_console.core.camera.states.v1.rpc import v1_rpc_response_to_v2
from local_console.core.commands.deploy import DeploymentSpec
from local_console.core.commands.deploy import StageNotifyFn
from local_console.core.commands.rpc_with_response import DirectCommandResponseBody
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration

logger = logging.getLogger(__name__)


class ReadyCameraV1(ConnectedCameraStateV1):

    def __init__(
        self,
        base: BaseStateProperties,
        first_report: DeviceConfiguration | None = None,
    ) -> None:
        super().__init__(base)

        if first_report:
            self._refresh_from_report(first_report)

    async def on_message_received(self, message: MQTTEvent) -> None:
        await super().on_message_received(message)

    async def start_app_deployment(
        self,
        target_spec: DeploymentSpec,
        event_flag: trio.Event,
        error_notify: Callable[[str], None],
        stage_notify_fn: StageNotifyFn | None = None,
        timeout_secs: int = 30,
    ) -> None:
        from local_console.core.camera.states.v1.deployment import ClearingAppCameraV1

        next_state = ClearingAppCameraV1(
            self._state_properties,
            target_spec,
            event_flag,
            error_notify,
            stage_notify_fn,
            timeout_secs,
        )
        await self._transit_to(next_state)

    async def run_command(
        self,
        module_id: str,
        method: str,
        params: dict[str, Any],
        extra: dict[str, Any],
    ) -> DirectCommandResponseBody:
        if module_id == "$system" and method == "StartUploadInferenceData":
            from local_console.core.camera.states.v1.streaming import StreamingCameraV1

            next_state = StreamingCameraV1(self._state_properties, params, extra)
            await self._transit_to(next_state)
            assert next_state._rpc_response
            return v1_rpc_response_to_v2(module_id, next_state._rpc_response)

        elif module_id == "$system" and method == "StopUploadInferenceData":
            await self._rpc_stop_streaming()
            assert self._rpc_response
            return v1_rpc_response_to_v2(module_id, self._rpc_response)
        else:
            await self._push_rpc(module_id, method, params, extra)
            assert self._rpc_response
            return v1_rpc_response_to_v2(module_id, self._rpc_response)

    async def perform_firmware_update(
        self,
        firmware_info: FirmwareInfo,
        event_flag: trio.Event,
        error_notify: Callable[[str], None],
        timeout_minutes: int = 4,
        use_configured_port: bool = False,
    ) -> None:
        from local_console.core.camera.states.v1.ota_sys import (
            UpdatingSysFirmwareCameraV1,
        )

        next_state = UpdatingSysFirmwareCameraV1(
            self._state_properties,
            firmware_info,
            event_flag,
            error_notify,
            timeout_minutes,
            use_configured_port,
        )
        await self._transit_to(next_state)

    async def deploy_sensor_model(
        self,
        package_file: Path,
        event_flag: trio.Event,
        error_notify: Callable,
        timeout_undeploy_secs: float = 30.0,
        timeout_deploy_secs: float = 90.0,
        use_configured_port: bool = False,
    ) -> None:
        from local_console.core.camera.states.v1.ota_sensor import (
            ClearingSensorModelCameraV1,
        )

        next_state = ClearingSensorModelCameraV1(
            self._state_properties,
            package_file,
            event_flag,
            error_notify,
            timeout_undeploy_secs,
            timeout_deploy_secs,
            use_configured_port,
        )
        await self._transit_to(next_state)
