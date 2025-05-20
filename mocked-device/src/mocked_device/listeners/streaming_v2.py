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

from mocked_device.mock_v2.device_v2 import MockDeviceV2
from mocked_device.mock_v2.ea_config import ProcessState
from mocked_device.mock_v2.ea_config import ResInfo
from mocked_device.mock_v2.ea_config import ResponseCode
from mocked_device.mock_v2.filters.app_configuration import AppConfigurationFilterV2
from mocked_device.mock_v2.state_machines.streaming_machine import StreamingMachineV2
from mocked_device.mqtt.event import TopicListener
from mocked_device.mqtt.values import TargetedMqttMessage

logger = logging.getLogger(__name__)


class StreamingV2Listener(TopicListener):

    def __init__(self, device: MockDeviceV2):
        self._device = device
        self._filter = AppConfigurationFilterV2()
        self._state_machine = StreamingMachineV2(device)

    def topic(self) -> str:
        return self._filter.topic()

    def handle(self, message: TargetedMqttMessage) -> None:
        incoming_edgeapp_conf = self._filter.filter(message)
        if not incoming_edgeapp_conf:
            return

        """
        At this point, it can be decided whether there is an error,
        and update the device status accordingly. If no error,
        then the state machine can be started.
        """
        req_id = incoming_edgeapp_conf.req_info.req_id
        incoming_edgeapp_conf.req_info = None
        incoming_edgeapp_conf.res_info = ResInfo(
            res_id=req_id, code=ResponseCode.OK, detail_msg="ok"
        )
        self._device.set_edge_app_configuration(incoming_edgeapp_conf)

        full_edgeapp_conf = self._device.status.single_app_status.spec
        cs = full_edgeapp_conf.common_settings
        if cs and cs.process_state and cs.port_settings:
            any_upload_enabled = (
                cs.port_settings.input_tensor and cs.port_settings.input_tensor.enabled
            ) or (cs.port_settings.metadata and cs.port_settings.metadata.enabled)
            if (
                cs.process_state == ProcessState.RUNNING
                and not self._state_machine.is_active
            ):
                if any_upload_enabled:
                    self._state_machine.start_with(cs)
                else:
                    logger.info("Edge App set to running, no uploads enabled yet.")
            elif self._state_machine.is_active and not any_upload_enabled:
                self._state_machine.stop()
            else:
                status = "active" if self._state_machine.is_active else "inactive"
                logger.warning(
                    f"Attempted to set state {cs.process_state.name} but streaming machine is {status} (ProcessState = {cs.process_state})"
                )
                return

            # The device emits a status report immediately
            self._device.send_status()
