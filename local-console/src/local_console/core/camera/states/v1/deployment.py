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
from local_console.core.camera.enums import DeployStage
from local_console.core.camera.enums import MQTTSubTopics
from local_console.core.camera.enums import MQTTTopics
from local_console.core.camera.states.base import BaseStateProperties
from local_console.core.camera.states.base import MQTTEvent
from local_console.core.camera.states.v1.common import ConnectedCameraStateV1
from local_console.core.commands.deploy import DeploymentSpec
from local_console.core.commands.deploy import StageNotifyFn
from local_console.core.commands.deploy import verify_report
from local_console.core.helpers import publish_deploy
from local_console.core.schemas.schemas import DeploymentManifest
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.utils.timing import TimeoutBehavior

logger = logging.getLogger(__name__)


class ClearingAppCameraV1(ConnectedCameraStateV1):

    def __init__(
        self,
        base: BaseStateProperties,
        target_spec: DeploymentSpec,
        event_flag: trio.Event,
        error_notify: Callable[[str], None],
        stage_notify_fn: StageNotifyFn | None = None,
        timeout_secs: int = 30,
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
        await publish_deploy(self._mqtt.client, OnWireProtocol.EVP1, to_deploy)

    async def enter(self, nursery: trio.Nursery) -> None:
        await super().enter(nursery)

        # Deploy immediately, without comparing with current status, to speed-up the process.
        logger.debug("Pushing manifest now.")
        self._timeout_handler.spawn_in(nursery)
        await self._set_new_stage(DeployStage.WaitAppliedConfirmation)
        await publish_deploy(self._mqtt.client, OnWireProtocol.EVP1, self._to_deploy)

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
            status_report = json.loads(
                message.payload[MQTTSubTopics.DEPLOY_STATUS.value]
            )
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
                    next_state = DeployingAppCameraV1(
                        self._state_properties,
                        self._target,
                        self._finished,
                        self._error_notify,
                        self._stage_notify,
                    )
                    await self._transit_to(next_state)

    async def _stop(self) -> None:
        from local_console.core.camera.states.v1.ready import ReadyCameraV1

        await self._transit_to(ReadyCameraV1(self._state_properties))

    async def stop_deployment(self) -> None:
        # Manually triggered stop
        if self.stage not in (DeployStage.Done, DeployStage.Error):
            self._finished.set()
            if self._stage_notify:
                await self._stage_notify(DeployStage.Error, self._to_deploy)

        await self._stop()


class DeployingAppCameraV1(ConnectedCameraStateV1):

    def __init__(
        self,
        base: BaseStateProperties,
        target_spec: DeploymentSpec,
        event_flag: trio.Event,
        error_notify: Callable[[str], None],
        stage_notify_fn: StageNotifyFn | None = None,
        timeout_secs: int = 30,
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

        self.stage = DeployStage.WaitAppliedConfirmation
        self._timeout_handler = TimeoutBehavior(timeout_secs, self._on_timeout)

        self._to_deploy: DeploymentManifest | None = None

    async def enter(self, nursery: trio.Nursery) -> None:
        await super().enter(nursery)
        self._timeout_handler.spawn_in(nursery)

        self._to_deploy = self._target.render_for_webserver(self._http, self._id)
        self._target.enlist_files_in(self._http)

        # Deploy immediately, without comparing with current status, to speed-up the process.
        logger.debug("Pushing manifest now.")
        await self._set_new_stage(DeployStage.WaitAppliedConfirmation)
        await publish_deploy(self._mqtt.client, OnWireProtocol.EVP1, self._to_deploy)

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
        await self._set_new_stage(DeployStage.Error)

    async def on_message_received(self, message: MQTTEvent) -> None:
        await super().on_message_received(message)

        if (
            message.topic == MQTTTopics.ATTRIBUTES.value
            and MQTTSubTopics.DEPLOY_STATUS.value in message.payload
        ):
            status_report = json.loads(
                message.payload[MQTTSubTopics.DEPLOY_STATUS.value]
            )
            self._timeout_handler.tap()

            is_finished, matches, is_errored = verify_report(
                self._target.pre_deployment.deploymentId, status_report
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
                    self._error_notify("Error while deploying edge app")

            if should_terminate:
                await self._set_new_stage(next_stage)
                await self._stop()

    async def _stop(self) -> None:
        from local_console.core.camera.states.v1.ready import ReadyCameraV1

        self._finished.set()
        await self._transit_to(ReadyCameraV1(self._state_properties))

    async def stop_deployment(self) -> None:
        # Manually triggered stop
        if (
            self.stage not in (DeployStage.Done, DeployStage.Error)
            and self._stage_notify
        ):
            await self._stage_notify(DeployStage.Error, self._to_deploy)

        await self._stop()
