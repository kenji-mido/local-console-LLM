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
import time
from collections.abc import Sequence
from typing import Any

from mocked_device.device import AppStates
from mocked_device.device import MockDevice
from mocked_device.listeners.handshake import HandshakeListener
from mocked_device.mock_v1.device_v1 import APPLICATION_FAILURE_MARKER
from mocked_device.mock_v2.ea_config import EdgeAppSpec
from mocked_device.mock_v2.ea_config import ProcessState
from mocked_device.mock_v2.filters.device_configuration import DesiredDeviceConfig
from mocked_device.mock_v2.filters.handshake import HandshakeFilterV2
from mocked_device.mock_v2.filters.rpc import RPCCommandV2
from mocked_device.mock_v2.message import DeploymentStatus
from mocked_device.mock_v2.message import DirectCommandResponse
from mocked_device.mock_v2.message import DirectCommandResponseBody
from mocked_device.mock_v2.message import DirectGetImageRequest
from mocked_device.mock_v2.message import DirectGetImageResponse
from mocked_device.mock_v2.message import EventLogV2
from mocked_device.mock_v2.message import Instance
from mocked_device.mock_v2.message import InstanceStatus
from mocked_device.mock_v2.message import Module
from mocked_device.mock_v2.message import ModuleStatus
from mocked_device.mock_v2.message import ReconcileStatus
from mocked_device.mock_v2.message import ReportStatusV2
from mocked_device.mock_v2.message import ResInfoNoID
from mocked_device.mock_v2.message import SystemInfoV2
from mocked_device.mqtt.connection import MqttConnection
from mocked_device.mqtt.event import TopicListener
from mocked_device.mqtt.values import MqttMessage
from mocked_device.utils.data import merge_model_instances
from mocked_device.utils.fake import fake_image_base64
from mocked_device.utils.request import download
from mocked_device.utils.timeout import EVENT_WAITING_2S
from mocked_device.utils.topics import MqttTopics

logger = logging.getLogger(__name__)


class MockDeviceV2(MockDevice):

    EVENT_LOG_PERIOD = 15

    def __init__(self, conn: MqttConnection, listeners: Sequence[type[TopicListener]]):
        super().__init__(conn, listeners)
        self.status: ReportStatusV2 = ReportStatusV2()
        self.system_info: SystemInfoV2 = SystemInfoV2()
        self.event_log: EventLogV2 = EventLogV2()

        self.report_status_interval = 10

    def do_handshake(self) -> None:
        message_id = "10000"
        await_for_response = HandshakeListener(HandshakeFilterV2(message_id))
        self._conn.add_listener(await_for_response)
        handshake_message = MqttMessage(
            topic=MqttTopics.ATTRIBUTES_REQ.suffixed(message_id), payload=b"{}"
        )
        self.send_system_info()
        self.send_mqtt(handshake_message)
        EVENT_WAITING_2S.wait_for(lambda: await_for_response.finished)
        if not await_for_response.finished:
            logger.warning(
                f"Handshake timeout after {EVENT_WAITING_2S.timeout_in_seconds} seconds"
            )
        logger.info("Handshake made!")

        now = time.time()
        next_report = now
        next_event_log = now + 2  # Empirical observation
        while True:
            now = time.time()

            if now >= next_report:
                next_report += self.report_status_interval
                self.send_system_info()
                self.send_status()
                logger.info(
                    f"Report status send, next one in {self.report_status_interval} seconds."
                )

            if now >= next_event_log:
                next_event_log += self.EVENT_LOG_PERIOD
                self.send_event_log()

            # Sleep exactly until the closest event is due
            next_event_in = min(
                mark - time.time()
                for mark in (
                    next_event_log,
                    next_report,
                )
            )
            if next_event_in > 0:
                time.sleep(next_event_in)

    def send_system_info(self) -> None:
        self.send_mqtt(self.system_info.build())

    def set_edge_app_configuration(self, new_config: EdgeAppSpec) -> None:
        merge_model_instances(self.status.single_app_status.spec, new_config)

    def update_edge_app(self, content: Any) -> None:
        # Check if need to stop streaming
        ea_conf = self.status.single_app_status.spec
        cs = ea_conf.common_settings
        if cs and cs.process_state:
            if cs.process_state == ProcessState.RUNNING:
                logger.debug("Stopping ongoing streaming")

                # not sure why mypy requires this, since within this
                # nested conditional, this exact condition has been fulfilled
                assert self.status.single_app_status.spec.common_settings

                self.status.single_app_status.spec.common_settings.process_state = (
                    ProcessState.STOPPED
                )

        logger.debug("Starting app deployment")
        if not content.instanceSpecs:
            self.device_assets.application = AppStates.Empty
            self.system_info.deploymentStatus = DeploymentStatus(
                deploymentId=content.deploymentId, reconcileStatus=ReconcileStatus.OK
            )
            logger.info(f"App type {self.device_assets.application.value}")
            self.status.single_app_status.deployed = False
            logger.debug("Finished deleting app")
            return None

        for instance_id, instance in content.instanceSpecs.items():
            self.system_info.deploymentStatus.deploymentId = content.deploymentId
            module_id = instance.moduleId
            logger.debug(f"Parsing {content.modules[module_id].downloadUrl}")

            if APPLICATION_FAILURE_MARKER in str(
                content.modules[module_id].downloadUrl
            ):
                logger.debug("Failure marker found, returning failure")
                self.system_info.deploymentStatus.reconcileStatus = (
                    ReconcileStatus.APPLYING
                )
                self.system_info.deploymentStatus.modules = {
                    module_id: Module(
                        status=ModuleStatus.ERROR, failureMessage="Mock failure message"
                    )
                }
                self.send_system_info()
                self.send_status()
                logger.debug("Finished erroneous app deployment")

                return

            # Started deploying
            self.system_info.deploymentStatus.reconcileStatus = ReconcileStatus.APPLYING
            self.system_info.deploymentStatus.modules = {
                module_id: Module(status=ModuleStatus.DOWNLOADING)
            }
            self.send_system_info()
            self.send_status()
            time.sleep(0.5)

            download(str(content.modules[module_id].downloadUrl))
            if AppStates.Classification.value in str(
                content.modules[module_id].downloadUrl
            ):
                self.device_assets.application = AppStates.Classification
            if AppStates.Detection.value in str(content.modules[module_id].downloadUrl):
                self.device_assets.application = AppStates.Detection
            if AppStates.ZoneDetection.value in str(
                content.modules[module_id].downloadUrl
            ):
                self.device_assets.application = AppStates.ZoneDetection
            logger.info(f"App type {self.device_assets.application.value} deployed")

            # Completed deploy
            self.status.single_app_status.deployed = True
            self.system_info.deploymentStatus.reconcileStatus = ReconcileStatus.OK
            self.system_info.deploymentStatus.modules = {
                module_id: Module(status=ModuleStatus.OK)
            }
            self.system_info.deploymentStatus.instances = {
                instance_id: Instance(status=InstanceStatus.OK, moduleId=module_id)
            }
            self.send_system_info()
            self.send_status()

    def send_direct_image(self, command: RPCCommandV2 | None) -> None:
        if not command:
            return None
        command_data = command.params.get("direct-command-request")
        if not command_data or command_data.method != "direct_get_image":
            return

        try:
            DirectGetImageRequest.model_validate(json.loads(command_data.params))
        except Exception as e:
            logger.error("Failed to parse params as DirectGetImageRequest", exc_info=e)
            return

        response_topic = MqttTopics.RPC_RESP.suffixed(command_data.reqid)
        response_payload = DirectGetImageResponse(
            res_info=ResInfoNoID(code=0, detail_msg="ok"), image=fake_image_base64()
        )
        self.send_mqtt(
            MqttMessage(
                topic=response_topic,
                payload=DirectCommandResponse(
                    **{
                        "direct-command-response": DirectCommandResponseBody(
                            reqid=command_data.reqid,
                            response=response_payload.model_dump_json(),
                        )
                    }
                )
                .model_dump_json(by_alias=True, exclude_none=True)
                .encode(),
            )
        )

    def reboot(self, command: RPCCommandV2) -> None:
        logger.warning("Not yet implemented")

    def send_accepted(self, command: RPCCommandV2) -> None:
        logger.warning("Not yet implemented")

    def _send_module_error(self) -> None:
        logger.warning("Not yet implemented")

    def _update_device_configuration(self, conf: DesiredDeviceConfig) -> None:
        self.report_status_interval = conf.report_status_interval_min
