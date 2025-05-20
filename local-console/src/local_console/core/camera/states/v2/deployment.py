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
from typing import Callable

import trio
from local_console.core.camera.enums import ApplicationConfiguration
from local_console.core.camera.enums import DeployStage
from local_console.core.camera.enums import MQTTSubTopics
from local_console.core.camera.enums import MQTTTopics
from local_console.core.camera.states.base import BaseStateProperties
from local_console.core.camera.states.base import MQTTEvent
from local_console.core.camera.states.v2.common import ConnectedCameraStateV2
from local_console.core.camera.v2.components.edge_app import APP_CONFIG_KEY
from local_console.core.camera.v2.components.edge_app import EdgeAppCommonSettings
from local_console.core.camera.v2.components.edge_app import EdgeAppPortSettings
from local_console.core.camera.v2.components.edge_app import EdgeAppSpec
from local_console.core.camera.v2.components.edge_app import ProcessState
from local_console.core.camera.v2.components.edge_app import UploadSpec
from local_console.core.camera.v2.components.req_res_info import ReqInfo
from local_console.core.commands.deploy import DeploymentSpec
from local_console.core.commands.deploy import StageNotifyFn
from local_console.core.commands.deploy import verify_report
from local_console.core.helpers import publish_deploy
from local_console.core.schemas.schemas import DeploymentManifest
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.utils.random import random_id
from local_console.utils.timing import TimeoutBehavior
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class ClearingAppCameraV2(ConnectedCameraStateV2):

    def __init__(
        self,
        base: BaseStateProperties,
        target_spec: DeploymentSpec,
        event_flag: trio.Event,
        error_notify: Callable[[str], None],
        stage_notify_fn: StageNotifyFn | None = None,
        timeout_secs: float = 30.0,
    ) -> None:
        """
        Create a Deploy FSM with an empty manifest and
        see to its completion, to reset the camera to
        a blank deployment state.
        """
        super().__init__(base)
        self._target = target_spec
        self._finished = event_flag
        self._error_notify = error_notify
        self._stage_notify = stage_notify_fn

        self.stage = DeployStage.WaitFirstStatus
        self._timeout_handler = TimeoutBehavior(timeout_secs, self._on_timeout)

        empty_spec = DeploymentSpec.new_empty()
        self._to_deploy = DeploymentManifest(deployment=empty_spec.pre_deployment)

    async def _publish_deploy(self, to_deploy: DeploymentManifest) -> None:
        await publish_deploy(self._mqtt.client, OnWireProtocol.EVP2, to_deploy)

    async def enter(self, nursery: trio.Nursery) -> None:
        await super().enter(nursery)

        # Deploy immediately, without comparing with current status, to speed-up the process.
        logger.debug("Pushing manifest now.")
        self._timeout_handler.spawn_in(nursery)
        await self._set_new_stage(DeployStage.WaitAppliedConfirmation)
        await publish_deploy(self._mqtt.client, OnWireProtocol.EVP2, self._to_deploy)

    async def exit(self) -> None:
        await super().exit()
        self._timeout_handler.stop()

    async def _set_new_stage(self, new_stage: DeployStage) -> None:
        self.stage = new_stage
        if self._stage_notify:
            await self._stage_notify(self.stage, self._to_deploy)

    async def _on_timeout(self) -> None:
        logger.error("Timeout while attempting edge app deployment")
        await self._stop()
        await self._set_new_stage(DeployStage.Error)

    async def on_message_received(self, message: MQTTEvent) -> None:
        await super().on_message_received(message)

        if (
            message.topic == MQTTTopics.ATTRIBUTES.value
            and MQTTSubTopics.DEPLOY_STATUS.value in message.payload
        ):
            status_report = message.payload[MQTTSubTopics.DEPLOY_STATUS.value]
            self._timeout_handler.tap()

            is_finished, matches, is_errored = verify_report(
                self._to_deploy.deployment.deploymentId, status_report
            )
            should_terminate = False
            next_stage = self.stage
            if matches:
                if is_finished:
                    should_terminate = True
                    next_stage = DeployStage.Done
                    logger.info("Deployment complete")

                elif is_errored:
                    should_terminate = True
                    next_stage = DeployStage.Error
                    logger.error("Deployment errored")

            if should_terminate:
                if next_stage == DeployStage.Error:
                    self._error_notify("Error while clearing edge app")
                    self._finished.set()
                    await self._set_new_stage(next_stage)
                    await self._stop()

                elif next_stage == DeployStage.Done:
                    # Don't report the stage; instead, proceed to actual app deployment.
                    await self._next()

    async def _stop(self) -> None:
        from local_console.core.camera.states.v2.ready import ReadyCameraV2

        await self._transit_to(ReadyCameraV2(self._state_properties))

    async def _next(self) -> None:
        await self._transit_to(
            DeployingAppCameraV2(
                self._state_properties,
                self._target,
                self._finished,
                self._error_notify,
                self._stage_notify,
            )
        )

    async def stop_deployment(self) -> None:
        # Manually triggered stop
        if self.stage not in (DeployStage.Done, DeployStage.Error):
            self._finished.set()
            if self._stage_notify:
                await self._stage_notify(DeployStage.Error, self._to_deploy)

        await self._stop()


class DeployingAppCameraV2(ConnectedCameraStateV2):

    def __init__(
        self,
        base: BaseStateProperties,
        target_spec: DeploymentSpec,
        event_flag: trio.Event,
        error_notify: Callable[[str], None],
        stage_notify_fn: StageNotifyFn | None = None,
        timeout_secs: float = 30.0,
    ) -> None:
        """
        Create a Deploy FSM with the populated app manifest and
        see to its completion.
        """
        super().__init__(base)
        self._target = target_spec
        self._finished = event_flag
        self._error_notify = error_notify
        self._stage_notify = stage_notify_fn

        self.stage = DeployStage.WaitFirstStatus
        self._timeout_handler = TimeoutBehavior(timeout_secs, self._on_timeout)

        self._to_deploy: DeploymentManifest | None = None

    async def enter(self, nursery: trio.Nursery) -> None:
        await super().enter(nursery)
        self._timeout_handler.spawn_in(nursery)
        self._to_deploy = self._target.render_for_webserver(self._http, self._id)
        self._target.enlist_files_in(self._http)
        await self._set_new_stage(DeployStage.WaitFirstStatus)

    async def exit(self) -> None:
        await super().exit()
        self._timeout_handler.stop()
        self._target.delist_files_in(self._http)

    async def _set_new_stage(self, new_stage: DeployStage) -> None:
        self.stage = new_stage
        if self._stage_notify:
            await self._stage_notify(self.stage, self._to_deploy)

    async def _on_timeout(self) -> None:
        logger.error("Timeout while attempting edge app deployment")
        await self._stop()
        assert self._to_deploy
        await self._set_new_stage(DeployStage.Error)

    async def on_message_received(self, message: MQTTEvent) -> None:
        await super().on_message_received(message)

        if (
            message.topic == MQTTTopics.ATTRIBUTES.value
            and MQTTSubTopics.DEPLOY_STATUS.value in message.payload
        ):
            status_report = message.payload[MQTTSubTopics.DEPLOY_STATUS.value]
            self._timeout_handler.tap()

            dm = self._to_deploy
            assert dm
            is_finished, matches, is_errored = verify_report(
                dm.deployment.deploymentId, status_report
            )
            next_stage = self.stage

            if matches:
                if is_finished:
                    await self._set_new_stage(DeployStage.Done)
                    logger.info("Deployment complete")
                    await self._continue()

                elif is_errored:
                    await self._set_new_stage(DeployStage.Error)
                    logger.error("Deployment errored")
                    self._error_notify("Error while deploying edge app")
                    await self._stop()

            else:
                if self.stage == DeployStage.WaitFirstStatus:
                    logger.debug("Agent can receive deployments. Pushing manifest now.")
                    dm = self._to_deploy
                    assert dm
                    await publish_deploy(self._mqtt.client, OnWireProtocol.EVP2, dm)
                    next_stage = DeployStage.WaitAppliedConfirmation

                elif self.stage == DeployStage.WaitAppliedConfirmation:
                    if matches:
                        logger.debug(
                            "Deployment received, reconcile=%s",
                            status_report.get("reconcileStatus", "<null>"),
                        )
                        logger.info(
                            "Deployment received, waiting for reconcile completion"
                        )

                elif self.stage in (DeployStage.Done, DeployStage.Error):
                    logger.warning(
                        "Should not reach here! (status is %s)",
                        json.dumps(status_report),
                    )

                await self._set_new_stage(next_stage)

    async def _continue(self) -> None:
        await self._transit_to(
            ConfigureAppToRunning(
                self._state_properties, self._finished, self._error_notify
            )
        )

    async def _stop(self) -> None:
        from local_console.core.camera.states.v2.ready import ReadyCameraV2

        await self._transit_to(ReadyCameraV2(self._state_properties))

    async def stop_deployment(self) -> None:
        # Manually triggered stop
        if self.stage not in (DeployStage.Done, DeployStage.Error):
            self._finished.set()
            if self._stage_notify:
                await self._stage_notify(DeployStage.Error, self._to_deploy)

        await self._stop()


class ConfigureAppToRunning(ConnectedCameraStateV2):
    CONFIGURATION_TIMEOUT = 60

    def __init__(
        self,
        base: BaseStateProperties,
        event_flag: trio.Event,
        error_notify: Callable[[str], None],
    ) -> None:
        super().__init__(base)
        self._finished = event_flag
        self._error_notify = error_notify
        self.req_id: str | None = None
        self._configuration_timeout = TimeoutBehavior(
            self.CONNECTION_STATUS_TIMEOUT,
            self._on_configuration_timeout,
        )

    async def enter(self, nursery: trio.Nursery) -> None:
        await super().enter(nursery)
        logger.debug("Configuring edge app")

        self.req_id = random_id()
        config = EdgeAppSpec(
            req_info=ReqInfo(req_id=self.req_id),
            common_settings=EdgeAppCommonSettings(
                port_settings=EdgeAppPortSettings(
                    metadata=UploadSpec(enabled=False),
                    input_tensor=UploadSpec(enabled=False),
                ),
                process_state=ProcessState.RUNNING,
            ),
        )

        await super().send_configuration(
            ApplicationConfiguration.NAME, APP_CONFIG_KEY, config
        )
        if self._props_report.latest_edge_app_config:
            await super().send_configuration(
                ApplicationConfiguration.NAME,
                APP_CONFIG_KEY,
                self._props_report.latest_edge_app_config,
            )
        self._configuration_timeout.spawn_in(nursery)

    async def exit(self) -> None:
        logger.debug("Exiting edge app configuration")
        self._configuration_timeout.stop()
        await super().exit()

    async def on_message_received(self, message: MQTTEvent) -> None:
        await super().on_message_received(message)

        try:
            state = EdgeAppSpec.model_validate(
                self._state_properties.reported.edge_app.get(
                    ApplicationConfiguration.NAME, {}
                )
            )
        except ValidationError:
            pass

        if state.res_info and state.res_info.res_id == self.req_id:
            if (
                not state.common_settings
                or not state.common_settings.port_settings
                or not state.common_settings.port_settings.input_tensor
                or not state.common_settings.port_settings.metadata
                or state.common_settings.process_state != ProcessState.RUNNING
                or state.common_settings.port_settings.input_tensor.enabled
                or state.common_settings.port_settings.metadata.enabled
            ):
                logger.warning(f"Edge App wrongly configured: {state}")

            await self._back_to_ready()

    async def _on_configuration_timeout(self) -> None:
        logger.debug("On configuration timeout")
        self._error_notify("Timed out configuring edge app")
        await self._back_to_ready()

    async def _back_to_ready(self) -> None:
        from local_console.core.camera.states.v2.ready import ReadyCameraV2

        self._finished.set()
        await self._transit_to(ReadyCameraV2(self._state_properties))
