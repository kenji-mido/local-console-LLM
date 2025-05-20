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

from mocked_device.mock_v2.device_v2 import DirectCommandResponse
from mocked_device.mock_v2.device_v2 import DirectCommandResponseBody
from mocked_device.mock_v2.device_v2 import DirectGetImageRequest
from mocked_device.mock_v2.device_v2 import DirectGetImageResponse
from mocked_device.mock_v2.device_v2 import MockDeviceV2
from mocked_device.mock_v2.device_v2 import ResInfoNoID
from mocked_device.mock_v2.filters.rpc import RPCCommandV2
from mocked_device.mqtt.connection import MqttConnection
from mocked_device.mqtt.event import TopicListener
from mocked_device.mqtt.values import MqttMessage
from mocked_device.utils.topics import MqttTopics
from system_stub.camera import get_camera
from system_stub.message import SystemInfoRPI

logger = logging.getLogger(__name__)


class MockDeviceRPI(MockDeviceV2):

    def __init__(
        self,
        conn: MqttConnection,
        listeners: list[type[TopicListener]],
    ):
        super().__init__(conn, listeners)
        self.system_info: SystemInfoRPI = SystemInfoRPI()
        self.status.system_private_endpoint_settings.endpoint_url = conn.config.host
        self.status.system_private_endpoint_settings.endpoint_port = conn.config.port
        self.cam = get_camera()

    def send_direct_image(self, command: RPCCommandV2 | None) -> None:
        if not command:
            return None
        command_data = command.params.get("direct-command-request")
        if not command_data or command_data.method != "direct_get_image":
            return

        try:
            request = DirectGetImageRequest.model_validate_json(command_data.params)
        except Exception as e:
            logger.error("Failed to parse params as DirectGetImageRequest", exc_info=e)
            return

        response_topic = MqttTopics.RPC_RESP.suffixed(command_data.reqid)

        image = ""
        try:
            image = self.cam.get_image_b64(request)
        except Exception as e:
            logger.warning("Error while getting image", exc_info=e)

        code, detail_msg = (0, "ok") if image else (9, "failed_precondition")
        response_payload = DirectGetImageResponse(
            res_info=ResInfoNoID(code=code, detail_msg=detail_msg),
            image=image,
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

    def reboot(self, command: RPCCommandV2 | None) -> None:
        logger.warning("Not yet implemented")

    def send_accepted(self, command: RPCCommandV2 | None) -> None:
        logger.warning("Not yet implemented")

    def _send_module_error(self) -> None:
        logger.warning("Not yet implemented")
