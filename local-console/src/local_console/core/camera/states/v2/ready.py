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
from local_console.core.camera.states.base import BaseStateProperties
from local_console.core.camera.states.base import MQTTEvent
from local_console.core.camera.states.common import set_periodic_reports_for_v2
from local_console.core.camera.states.common import V2_PERIODIC_REPORT_TIMEOUT_SECS
from local_console.core.camera.states.v2.common import ConnectedCameraStateV2
from local_console.core.camera.v2.components.edge_app import APP_CONFIG_KEY
from local_console.core.camera.v2.components.edge_app import EdgeAppSpec
from local_console.core.camera.v2.components.edge_app import ProcessState
from local_console.core.camera.v2.edge_system_common import EdgeSystemCommon
from local_console.core.commands.deploy import DeploymentSpec
from local_console.core.commands.deploy import StageNotifyFn
from local_console.core.commands.rpc_with_response import DirectCommandResponse
from local_console.utils.timing import TimeoutBehavior
from pydantic import BaseModel
from pydantic import ValidationError

logger = logging.getLogger(__name__)


# MQTT constants
SYSINFO_TOPIC = "systemInfo"


class ReadyCameraV2(ConnectedCameraStateV2):

    def __init__(
        self,
        base: BaseStateProperties,
        first_report: EdgeSystemCommon | None = None,
    ) -> None:
        super().__init__(base)

        if first_report:
            self._refresh_from_report(first_report)

        self._periodic_reports_timeout = TimeoutBehavior(
            V2_PERIODIC_REPORT_TIMEOUT_SECS, self._set_periodic_reports
        )

    async def enter(self, nursery: trio.Nursery) -> None:
        await super().enter(nursery)

        # This takes care of ensuring the device reports its state
        # with bounded periodicity (expect to receive a message
        # within PERIODIC_REPORT_TIMEOUT seconds)
        self._periodic_reports_timeout.spawn_in(nursery)

    async def exit(self) -> None:
        await super().exit()
        self._periodic_reports_timeout.stop()

    async def _set_periodic_reports(self) -> None:
        await set_periodic_reports_for_v2(self._mqtt, V2_PERIODIC_REPORT_TIMEOUT_SECS)

    async def on_message_received(self, message: MQTTEvent) -> None:
        await super().on_message_received(message)
        self._periodic_reports_timeout.tap()

    async def start_app_deployment(
        self,
        target_spec: DeploymentSpec,
        event_flag: trio.Event,
        error_notify: Callable[[str], None],
        stage_notify_fn: StageNotifyFn | None = None,
        timeout_secs: int = 30,
    ) -> None:
        from local_console.core.camera.states.v2.deployment import ClearingAppCameraV2

        next_state = ClearingAppCameraV2(
            self._state_properties,
            target_spec,
            event_flag,
            error_notify,
            stage_notify_fn,
            timeout_secs,
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
        from local_console.core.camera.states.v2.ota_sensor import (
            ClearingAppCameraThenUndeployModelV2,
        )

        next_state = ClearingAppCameraThenUndeployModelV2(
            self._state_properties,
            package_file,
            event_flag,
            error_notify,
            timeout_undeploy_secs,
            timeout_deploy_secs,
            use_configured_port,
        )
        await self._transit_to(next_state)

    async def send_configuration(
        self, module_id: str, property_name: str, data: dict[str, Any] | BaseModel
    ) -> None:
        if property_name == APP_CONFIG_KEY:
            # This is potentially a payload to get streaming started
            try:
                ea_config = EdgeAppSpec.model_validate(data)
                cs = ea_config.common_settings
                if cs:
                    ps = cs.process_state
                    if ps == ProcessState.RUNNING:
                        # it is, so do the state transition
                        await self._start_streaming(module_id, ea_config)

                        # The payload will be enriched and sent by the
                        # `enter` phase of the transition, so we avoid the
                        # dispatch of the original payload.
                        return
            except ValidationError:
                pass

        await super().send_configuration(module_id, property_name, data)

    async def _start_streaming(self, target_module: str, params: EdgeAppSpec) -> None:
        from local_console.core.camera.states.v2.streaming import StreamingCameraV2

        next_state = StreamingCameraV2(self._state_properties, target_module, params)
        await self._transit_to(next_state)

    async def run_command(
        self,
        module_id: str,
        method: str,
        params: dict[str, Any],
        extra: dict[str, Any],
    ) -> DirectCommandResponse:
        if module_id == "$system" and method == "direct_get_image":
            should_stop = extra.get("stop", False)
            if should_stop:
                return DirectCommandResponse.empty_ok()

            from local_console.core.camera.states.v2.imagecap import (
                ImageCapturingCameraV2,
            )

            next_state = ImageCapturingCameraV2(self._state_properties, params, extra)
            await self._transit_to(next_state)
            assert next_state._rpc_response
            return next_state._rpc_response

        else:
            return await super().run_command(module_id, method, params, extra)
