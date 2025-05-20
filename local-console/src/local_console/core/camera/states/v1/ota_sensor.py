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
from local_console.clients.agent import Agent
from local_console.core.camera.enums import MQTTTopics
from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.camera.states.base import BaseStateProperties
from local_console.core.camera.states.base import MQTTEvent
from local_console.core.camera.states.v1.common import ConnectedCameraStateV1
from local_console.core.camera.states.v1.common import EA_STATE_TOPIC
from local_console.core.commands.ota_deploy import configuration_spec
from local_console.core.commands.ota_deploy import get_network_id
from local_console.core.commands.ota_deploy import get_network_ids
from local_console.core.config import Config
from local_console.core.helpers import publish_configure
from local_console.core.schemas.edge_cloud_if_v1 import DnnDelete
from local_console.core.schemas.edge_cloud_if_v1 import DnnDeleteBody
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.servers.webserver import combine_url_components

logger = logging.getLogger(__name__)


class ClearingSensorModelCameraV1(ConnectedCameraStateV1):

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
        super().__init__(base)
        self.package_file = package_file
        self._finished = event_flag
        self.notify_fn = error_notify
        self._timeout_undeploy_secs = timeout_undeploy_secs
        self._timeout_deploy_secs = timeout_deploy_secs
        self._use_configured_port = use_configured_port

        self._timeout_scope: trio.CancelScope = trio.move_on_after(
            self._timeout_undeploy_secs
        )
        self.network_id = get_network_id(self.package_file)
        self._will_transit = False

    async def enter(self, nursery: trio.Nursery) -> None:
        await super().enter(nursery)
        await nursery.start(self._clear_sensor_model_task)

    async def exit(self) -> None:
        await super().exit()
        self._timeout_scope.cancel()

    async def _clear_sensor_model_task(
        self, *, task_status: Any = trio.TASK_STATUS_IGNORED
    ) -> None:
        config_device = Config().get_device_config(self._id)
        ephemeral_agent = Agent(config_device.mqtt.port)

        waiter = trio.Event()
        logger.debug("Firmware update operation will start.")
        with self._timeout_scope:
            async with (
                ephemeral_agent.mqtt_scope(
                    [MQTTTopics.ATTRIBUTES_REQ.value, MQTTTopics.ATTRIBUTES.value]
                ),
            ):
                logger.debug(
                    f"Status before OTA is: {self._props_report.sensor_fw_ota_status}"
                )

                await publish_configure(
                    ephemeral_agent,
                    OnWireProtocol.EVP1,
                    "backdoor-EA_Main",
                    "placeholder",
                    DnnDelete(
                        OTA=DnnDeleteBody(DeleteNetworkID=self.network_id)
                    ).model_dump_json(),
                )

                task_status.started()
                await waiter.wait()
                # From this point on, the OTA process is stimulated
                # with the messages processed at on_message_received()

        if self._timeout_scope.cancelled_caught and not self._will_transit:
            self.notify_fn(
                f"Error while undeploying sensor model {self.network_id} "
                f"with UpdateStatus={self._props_report.sensor_fw_ota_status}"
            )
            self._finished.set()

            # Need to transit back to the ready-idle state
            from local_console.core.camera.states.v1.ready import ReadyCameraV1

            await self._transit_to(ReadyCameraV1(self._state_properties))

    async def on_message_received(self, message: MQTTEvent) -> None:
        await super().on_message_received(message)
        if (
            message.topic == MQTTTopics.ATTRIBUTES.value
            and EA_STATE_TOPIC in message.payload
        ):
            self._timeout_scope.deadline += self._timeout_undeploy_secs

            ota_status = self._props_report.sensor_fw_ota_status
            if ota_status and self._props_report.dnn_versions is not None:
                deployed_dnn_model_versions = get_network_ids(
                    self._props_report.dnn_versions
                )
                logger.debug(
                    f"Deployed DNN model version: {deployed_dnn_model_versions}"
                )
                model_is_deployed = self.network_id in deployed_dnn_model_versions

                # If a previous operation failed and the model is not present, the update status remains as failed.
                if not model_is_deployed and ota_status.lower() in ["done", "failed"]:
                    logger.debug(f"DNN model unload operation result is: {ota_status}")
                    self._will_transit = True
                    await self._transit_to(
                        UpdateSensorModelCameraV1(
                            self._state_properties,
                            self.package_file,
                            self._finished,
                            self.notify_fn,
                            self._timeout_deploy_secs,
                            self._use_configured_port,
                        )
                    )


class UpdateSensorModelCameraV1(ConnectedCameraStateV1):

    def __init__(
        self,
        base: BaseStateProperties,
        package_file: Path,
        event_flag: trio.Event,
        error_notify: Callable,
        timeout_secs: float = 90.0,
        use_configured_port: bool = False,
    ) -> None:
        super().__init__(base)
        self.package_file = package_file
        self._finished = event_flag
        self.notify_fn = error_notify
        self._timeout_secs = timeout_secs
        self._use_configured_port = use_configured_port

        self._timeout_scope: trio.CancelScope = trio.move_on_after(self._timeout_secs)
        self._previous_report = self._props_report.model_copy()
        self._previous_status = self._previous_report.sensor_fw_ota_status
        self.network_id = get_network_id(self.package_file)

    async def enter(self, nursery: trio.Nursery) -> None:
        await super().enter(nursery)
        await nursery.start(self._update_sensor_model_task)

    async def exit(self) -> None:
        await super().exit()
        self._timeout_scope.cancel()
        self._finished.set()
        self._http.delist_file(self.package_file)

    async def _update_sensor_model_task(
        self, *, task_status: Any = trio.TASK_STATUS_IGNORED
    ) -> None:
        config_device = Config().get_device_config(self._id)
        ephemeral_agent = Agent(config_device.mqtt.port)

        with self._timeout_scope:
            logger.debug("Firmware update operation will start.")
            async with (
                ephemeral_agent.mqtt_scope(
                    [MQTTTopics.ATTRIBUTES_REQ.value, MQTTTopics.ATTRIBUTES.value]
                ),
            ):
                self._previous_status = self._props_report.sensor_fw_ota_status
                logger.debug(f"Status before OTA is: {self._previous_status}")

                url_root = self._http.url_root_at(self._id)
                url_path = self._http.enlist_file(self.package_file)
                url = combine_url_components(url_root, url_path)
                spec = configuration_spec(
                    OTAUpdateModule.DNNMODEL, self.package_file, url
                ).model_dump_json()
                logger.debug(f"Update spec is: {spec}")

                await publish_configure(
                    ephemeral_agent,
                    OnWireProtocol.EVP1,
                    "backdoor-EA_Main",
                    "placeholder",
                    spec,
                )

                task_status.started()
                # From this point on, the OTA process is stimulated
                # with the messages processed at on_message_received()
                await self._finished.wait()

        if self._timeout_scope.cancelled_caught:
            self.notify_fn(
                f"Error while undeploying sensor model {self.network_id} "
                f"with UpdateStatus={self._props_report.sensor_fw_ota_status}"
            )
            await self._transition_out()

    async def on_message_received(self, message: MQTTEvent) -> None:
        await super().on_message_received(message)
        if (
            message.topic == MQTTTopics.ATTRIBUTES.value
            and EA_STATE_TOPIC in message.payload
        ):
            self._timeout_scope.deadline += self._timeout_secs

            ota_status = self._props_report.sensor_fw_ota_status
            previous_status = self._previous_report.sensor_fw_ota_status
            if (
                ota_status
                and ota_status != previous_status
                and self._props_report.dnn_versions is not None
            ):

                deployed_dnn_model_versions = get_network_ids(
                    self._props_report.dnn_versions
                )
                logger.debug(
                    f"Deployed DNN model version: {deployed_dnn_model_versions}"
                )
                model_is_deployed = self.network_id in deployed_dnn_model_versions

                if ota_status.lower() == "failed":
                    self.notify_fn("Failed to deploy sensor model")
                    await self._transition_out()

                if ota_status.lower() == "done" and model_is_deployed:
                    logger.debug(
                        f"Sensor model upload operation result is: {ota_status}"
                    )
                    await self._transition_out()

            self._previous_report = self._props_report.model_copy()

    async def _transition_out(self) -> None:
        # Need to transit back to the ready-idle state
        from local_console.core.camera.states.v1.ready import ReadyCameraV1

        await self._transit_to(ReadyCameraV1(self._state_properties))
