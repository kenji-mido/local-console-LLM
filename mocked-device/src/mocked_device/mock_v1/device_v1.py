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

from mocked_device.device import AppStates
from mocked_device.device import MockDevice
from mocked_device.listeners.handshake import HandshakeListener
from mocked_device.mock_v1.filters.handshake import HandshakeFilterV1
from mocked_device.mock_v1.filters.rpc import RPCCommand
from mocked_device.mock_v1.message import DeploymentStatus
from mocked_device.mock_v1.message import EventLog
from mocked_device.mock_v1.value import DeploymentConfig
from mocked_device.mqtt.connection import MqttConnection
from mocked_device.mqtt.event import TopicListener
from mocked_device.mqtt.values import MqttMessage
from mocked_device.utils.fake import fake_image_base64
from mocked_device.utils.json import json_bytes
from mocked_device.utils.random import random_id
from mocked_device.utils.request import download
from mocked_device.utils.timeout import EVENT_WAITING_2S
from mocked_device.utils.topics import MqttTopics

logger = logging.getLogger(__name__)

APPLICATION_FAILURE_MARKER = "app_fail"


class MockDeviceV1(MockDevice):
    def __init__(self, conn: MqttConnection, listeners: Sequence[type[TopicListener]]):
        super().__init__(conn, listeners)
        self.status: DeploymentStatus = DeploymentStatus()
        self.event_log: EventLog = EventLog()

    def do_handshake(self) -> None:
        while True:
            message_id = random_id()
            await_for_response = HandshakeListener(HandshakeFilterV1(message_id))
            self._conn.add_listener(await_for_response)
            handshake_message = MqttMessage(
                topic=MqttTopics.ATTRIBUTES_REQ.suffixed(message_id), payload=b"{}"
            )
            self.send_mqtt(handshake_message)
            EVENT_WAITING_2S.wait_for(lambda: await_for_response.finished)
            if not await_for_response.finished:
                logger.warning(
                    f"Handshake timeout after {EVENT_WAITING_2S.timeout_in_seconds} seconds"
                )
            self.send_status()
            self.send_event_log()
            logger.info("Handshake made, next one in 60 seconds.")
            time.sleep(60)

    def update_edge_app(self, content: DeploymentConfig) -> None:
        if not content.modules:
            self.device_assets.application = AppStates.Empty
        for name, module in content.modules.items():
            logger.debug(f"parsing {name} {module.download_url}")
            if APPLICATION_FAILURE_MARKER in str(module.download_url):
                logger.debug("failure marker found, returning failure")
                self._send_module_error()
                return
            download(str(module.download_url))
            if AppStates.Classification.value in str(module.download_url):
                self.device_assets.application = AppStates.Classification
            if AppStates.Detection.value in str(module.download_url):
                self.device_assets.application = AppStates.Detection
            if AppStates.ZoneDetection.value in str(module.download_url):
                self.device_assets.application = AppStates.ZoneDetection
        body = {
            "deploymentId": content.deployment_id,
            "reconcileStatus": "ok",
        }
        response = {"deploymentStatus": json.dumps(body)}
        msg = MqttMessage(
            topic=MqttTopics.ATTRIBUTES.value, payload=json_bytes(response)
        )
        self.send_mqtt(msg)
        logger.debug(f"Finished app download {self.device_assets.application}")

    def send_direct_image(self, command: RPCCommand) -> None:
        if command and command.method == "DirectGetImage":
            response_topic = MqttTopics.RPC_RESP.suffixed(command.message_id)
            json_payload = {"response": {"Image": fake_image_base64()}}
            self.send_mqtt(
                MqttMessage(topic=response_topic, payload=json_bytes(json_payload))
            )

    def reboot(self, command: RPCCommand) -> None:
        self.device_assets.application = AppStates.Empty
        prev_port = self.status.Network.ProxyPort
        prev_dnns = self.status.Version.DnnModelVersion
        self.status = DeploymentStatus()
        self.status.Network.ProxyPort = prev_port
        self.status.Version.DnnModelVersion = prev_dnns
        self.send_accepted(command)
        self.send_status()
        self.send_event_log()

    def send_accepted(self, command: RPCCommand) -> None:
        response_topic = MqttTopics.RPC_RESP.suffixed(command.message_id)
        json_payload = {"response": {"result": "Accepted"}}
        self.send_mqtt(
            MqttMessage(topic=response_topic, payload=json_bytes(json_payload))
        )

    def _send_module_error(self) -> None:
        response = {"modules": json.dumps({"moduleId_000": {"status": "error"}})}
        msg = MqttMessage(
            topic=MqttTopics.ATTRIBUTES.value, payload=json_bytes(response)
        )
        self.send_mqtt(msg)
