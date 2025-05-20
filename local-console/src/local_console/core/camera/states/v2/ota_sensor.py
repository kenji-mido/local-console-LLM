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
from typing import Callable
from typing import cast

import trio
from local_console.core.camera.enums import MQTTTopics
from local_console.core.camera.states.base import BaseStateProperties
from local_console.core.camera.states.base import MQTTEvent
from local_console.core.camera.states.v2.common import ConnectedCameraStateV2
from local_console.core.camera.states.v2.deployment import ClearingAppCameraV2
from local_console.core.camera.states.v2.ready import ReadyCameraV2
from local_console.core.camera.v2.components.private_deploy_ai_model import (
    PrivateDeployAIModel,
)
from local_console.core.camera.v2.components.private_deploy_ai_model import (
    ProgressState,
)
from local_console.core.camera.v2.components.private_deploy_ai_model import Target
from local_console.core.camera.v2.components.req_res_info import ResponseCode
from local_console.core.camera.v2.edge_system_common import EdgeSystemCommon
from local_console.core.commands.deploy import DeploymentSpec
from local_console.core.commands.ota_deploy import get_network_id
from local_console.core.commands.ota_deploy import get_package_hash
from local_console.core.commands.ota_deploy import get_package_version
from local_console.servers.webserver import combine_url_components
from local_console.utils.timing import TimeoutBehavior

logger = logging.getLogger(__name__)

DEPLOY_ALIAS = cast(
    str, EdgeSystemCommon.model_fields["private_deploy_ai_model"].serialization_alias
)
DEPLOY_KEY_TARGET, DEPLOY_KEY_PROPERTY = DEPLOY_ALIAS.split("/")[1:3]


class ClearingSensorModelCameraV2(ConnectedCameraStateV2):

    def __init__(
        self,
        base: BaseStateProperties,
        package_file: Path,
        event_flag: trio.Event,
        error_notify: Callable[[str], None],
        timeout_undeploy_secs: float = 30.0,
        timeout_deploy_secs: float = 90.0,
        use_configured_port: bool = False,
    ) -> None:
        super().__init__(base)
        self.package_file = package_file
        self._finished = event_flag
        self._error_notify = error_notify
        self._timeout_deploy_secs = timeout_deploy_secs
        self._use_configured_port = use_configured_port

        self._timeout_handler = TimeoutBehavior(timeout_undeploy_secs, self._on_abort)
        self.req_id = self.generate_req()

        self.last_model_count = 0
        if base.reported.dnn_versions is not None:
            self.last_model_count = sum(
                int(ver != "") for ver in base.reported.dnn_versions
            )

    async def enter(self, nursery: trio.Nursery) -> None:
        await super().enter(nursery)
        self._timeout_handler.spawn_in(nursery)

        logger.debug("DNN model clearing operation will start.")
        delete_msg = PrivateDeployAIModel(req_info=self.req_id, targets=[])
        await self.send_configuration(
            DEPLOY_KEY_TARGET,
            DEPLOY_KEY_PROPERTY,
            delete_msg.model_dump(by_alias=True, exclude_unset=True),
        )

    async def exit(self) -> None:
        await super().exit()
        self._timeout_handler.stop()

    async def _stop(self) -> None:
        from local_console.core.camera.states.v2.ready import ReadyCameraV2

        await self._transit_to(ReadyCameraV2(self._state_properties))

    async def _on_abort(self) -> None:
        self._error_notify(
            "Error while clearing sensor models"
            f"with UpdateStatus={self._props_report.sensor_fw_ota_status}"
        )
        await self._stop()

        # An abort marks the end of the overall process.
        self._finished.set()

    async def on_message_received(self, message: MQTTEvent) -> None:
        await super().on_message_received(message)

        if message.topic != MQTTTopics.ATTRIBUTES.value:
            return

        current_model_count = 0
        if self._props_report.dnn_versions is not None:
            current_model_count = sum(
                int(ver != "") for ver in self._props_report.dnn_versions
            )

        update = EdgeSystemCommon.model_validate(message.payload)
        deploy_report: PrivateDeployAIModel | None = update.private_deploy_ai_model

        if not deploy_report:
            return

        # At this point, the message is an update of our process, so tap the timeout timer.
        self._timeout_handler.tap()
        self.last_model_count = current_model_count

        if deploy_report.res_info:
            res_info = deploy_report.res_info
            if res_info.res_id == self.req_id.req_id:
                if res_info.code != ResponseCode.OK:
                    await self._on_abort()
                else:
                    if current_model_count == 0:
                        logger.debug("DNN model clearing operation completed.")
                        await self._next()

    async def _next(self) -> None:
        await self._transit_to(
            UpdateSensorModelCameraV2(
                self._state_properties,
                self.package_file,
                self._finished,
                self._error_notify,
                self._timeout_deploy_secs,
                self._use_configured_port,
            )
        )


class UpdateSensorModelCameraV2(ConnectedCameraStateV2):

    def __init__(
        self,
        base: BaseStateProperties,
        package_file: Path,
        event_flag: trio.Event,
        error_notify: Callable[[str], None],
        timeout_secs: float = 90.0,
        use_configured_port: bool = False,
    ) -> None:
        super().__init__(base)
        self.package_file = package_file
        self._finished = event_flag
        self._error_notify = error_notify
        self._use_configured_port = use_configured_port

        self._timeout_handler = TimeoutBehavior(timeout_secs, self._on_abort)
        self._previous_report = self._props_report.model_copy()
        self._previous_status = self._previous_report.sensor_fw_ota_status
        self.req_id = self.generate_req()
        self.model_id = get_network_id(self.package_file)
        self.desired: PrivateDeployAIModel | None = None

    async def enter(self, nursery: trio.Nursery) -> None:
        await super().enter(nursery)
        self._timeout_handler.spawn_in(nursery)

        url_root = self._http.url_root_at(self._id)
        url_path = self._http.enlist_file(self.package_file)
        url = combine_url_components(url_root, url_path)
        self.desired = PrivateDeployAIModel(
            req_info=self.req_id,
            targets=[
                Target(
                    chip="sensor_chip",
                    version=get_package_version(self.package_file),
                    package_url=url,
                    hash=get_package_hash(self.package_file),
                    size=self.package_file.stat().st_size,
                )
            ],
        )
        await self.send_configuration(
            DEPLOY_KEY_TARGET,
            DEPLOY_KEY_PROPERTY,
            self.desired.model_dump(by_alias=True, exclude_unset=True),
        )

    async def exit(self) -> None:
        await super().exit()
        self._timeout_handler.stop()
        self._http.delist_file(self.package_file)

    async def _stop(self) -> None:
        from local_console.core.camera.states.v2.ready import ReadyCameraV2

        await self._transit_to(ReadyCameraV2(self._state_properties))

    async def _on_abort(self) -> None:
        self._error_notify(
            f"Error while updating sensor model {self.model_id} "
            f"with UpdateStatus={self._props_report.sensor_fw_ota_status}"
        )
        await self._stop()

    async def on_message_received(self, message: MQTTEvent) -> None:
        await super().on_message_received(message)

        if message.topic != MQTTTopics.ATTRIBUTES.value:
            return

        update = EdgeSystemCommon.model_validate(message.payload)
        if not update.private_deploy_ai_model:
            return

        current: PrivateDeployAIModel = update.private_deploy_ai_model

        # At this point, the message is an update of our process, so tap the timeout timer.
        self._timeout_handler.tap()

        # Other states are either OK or Failed (with its variants)
        num_pending = sum(
            target.process_state
            in {
                ProgressState.REQUEST_RECEIVED,
                ProgressState.DOWNLOADING,
                ProgressState.INSTALLING,
            }
            for target in current.targets
        )

        all_done = False
        if num_pending == 0:
            all_done = all(
                target.process_state == ProgressState.DONE for target in current.targets
            )

        if current.res_info:
            res_info = current.res_info
            if res_info.res_id == self.req_id.req_id:
                if res_info.code != ResponseCode.OK:
                    await self._on_abort()
                else:
                    if all_done:
                        logger.debug(
                            f"DNN model {self.model_id} upload operation completed."
                        )
                        await self._stop()


class ClearingAppCameraThenUndeployModelV2(ClearingAppCameraV2):
    def __init__(
        self,
        base: BaseStateProperties,
        package_file: Path,
        event_flag: trio.Event,
        error_notify: Callable,
        timeout_undeploy_secs: float = 30.0,
        timeout_deploy_secs: float = 90.0,
        use_configured_port: bool = False,
    ) -> None:
        super().__init__(
            base,
            DeploymentSpec.new_empty(),
            event_flag,
            error_notify,
            timeout_secs=timeout_undeploy_secs,
        )
        self.package_file = package_file
        self.event_flag = event_flag
        self.error_notify = error_notify
        self.timeout_undeploy_secs = timeout_undeploy_secs
        self.timeout_deploy_secs = timeout_deploy_secs
        self.use_configured_port = use_configured_port

    async def _next(self) -> None:
        logger.debug("Edge App undeployed.")
        await self._transit_to(
            ClearingSensorModelThenDeployModelV2(
                self._state_properties,
                self.package_file,
                self.event_flag,
                self.error_notify,
                self.timeout_undeploy_secs,
                self.timeout_deploy_secs,
                self.use_configured_port,
            )
        )


class ClearingSensorModelThenDeployModelV2(ClearingSensorModelCameraV2):
    async def _next(self) -> None:
        logger.debug("AI Model undeployed.")
        await self._transit_to(
            UpdateSensorThenDeployAppV2(
                self._state_properties,
                self.package_file,
                self._finished,
                self._error_notify,
                self._timeout_deploy_secs,
                self._use_configured_port,
            )
        )


class UpdateSensorThenDeployAppV2(UpdateSensorModelCameraV2):
    async def _stop(self) -> None:

        if self._props_report.latest_deployment_spec:
            from local_console.core.camera.states.v2.deployment import (
                DeployingAppCameraV2,
            )

            logger.debug("Model deployed. Re-deploying the previous Edge App.")
            # recover latest deployed edge app
            await self._transit_to(
                DeployingAppCameraV2(
                    self._state_properties,
                    self._props_report.latest_deployment_spec,
                    self._finished,
                    self._error_notify,
                    timeout_secs=self._timeout_handler.timeout_secs,
                )
            )
            return

        logger.debug(
            "Model deployed. No previous Edge App found. Transitioning to Ready."
        )
        self._finished.set()
        await self._transit_to(ReadyCameraV2(self._state_properties))
