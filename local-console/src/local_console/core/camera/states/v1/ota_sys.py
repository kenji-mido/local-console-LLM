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
from tempfile import TemporaryDirectory
from typing import Any
from typing import Callable

import trio
from local_console.clients.agent import Agent
from local_console.core.camera.enums import MQTTTopics
from local_console.core.camera.firmware import FirmwareInfo
from local_console.core.camera.firmware import FirmwareValidationStatus
from local_console.core.camera.firmware import process_firmware_file
from local_console.core.camera.firmware import progress_update_checkpoint
from local_console.core.camera.firmware import validate_firmware_file
from local_console.core.camera.states.base import BaseStateProperties
from local_console.core.camera.states.base import MQTTEvent
from local_console.core.camera.states.v1.common import ConnectedCameraStateV1
from local_console.core.commands.ota_deploy import configuration_spec
from local_console.core.config import Config
from local_console.core.error.base import UserException
from local_console.core.helpers import publish_configure
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.servers.webserver import combine_url_components

logger = logging.getLogger(__name__)


class UpdatingSysFirmwareCameraV1(ConnectedCameraStateV1):

    def __init__(
        self,
        base: BaseStateProperties,
        firmware_info: FirmwareInfo,
        event_flag: trio.Event,
        error_notify: Callable,
        timeout_minutes: int = 4,
        use_configured_port: bool = False,
    ) -> None:
        super().__init__(base)
        self.firmware_info = firmware_info
        self._finished = event_flag
        self.notify_fn = error_notify
        self._use_configured_port = use_configured_port

        self._timeout_secs = 60 * timeout_minutes
        self._timeout_scope: trio.CancelScope = trio.move_on_after(self._timeout_secs)

        self._previous_report = self._props_report.model_copy()
        self._previous_status = self._previous_report.cam_fw_ota_status

    async def enter(self, nursery: trio.Nursery) -> None:
        await super().enter(nursery)
        await nursery.start(self._update_firmware_task)

    async def exit(self) -> None:
        await super().exit()
        self._timeout_scope.cancel()
        self._finished.set()

    async def _update_firmware_task(
        self, *, task_status: Any = trio.TASK_STATUS_IGNORED
    ) -> None:
        with TemporaryDirectory() as temporary_dir:
            tmp_dir = Path(temporary_dir)

            tmp_firmware, firmware_header = process_firmware_file(
                tmp_dir, self.firmware_info
            )
            if firmware_header:
                self.firmware_info.version = firmware_header.firmware_version

            validation_status = FirmwareValidationStatus.INVALID
            try:
                validation_status = validate_firmware_file(
                    self.firmware_info.path,
                    self.firmware_info.type,
                    self.firmware_info.version,
                    self._props_report,
                    firmware_header,
                )
            except UserException as e:
                self.notify_fn(str(e))
                return

            if validation_status == FirmwareValidationStatus.INVALID:
                self.notify_fn("Firmware validation failed.")
                return
            elif validation_status == FirmwareValidationStatus.SAME_FIRMWARE:
                logger.debug("No action needed. Firmware update operation is finished.")
                self.notify_fn("The target Firmware version is already deployed")
                return

            config_device = Config().get_device_config(self._id)
            ephemeral_agent = Agent(config_device.mqtt.port)

            url_root = self._http.url_root_at(self._id)
            url_path = self._http.enlist_file(tmp_firmware)
            url = combine_url_components(url_root, url_path)

            with self._timeout_scope:
                logger.debug("Firmware update operation will start.")
                async with (
                    ephemeral_agent.mqtt_scope(
                        [MQTTTopics.ATTRIBUTES_REQ.value, MQTTTopics.ATTRIBUTES.value]
                    ),
                ):
                    update_spec = configuration_spec(
                        self.firmware_info.type,
                        tmp_firmware,
                        url,
                    )
                    # Use version specified by the user
                    update_spec.OTA.DesiredVersion = self.firmware_info.version

                    payload = update_spec.model_dump_json()
                    logger.debug(f"Update spec is: {payload}")

                    self._previous_status = self._props_report.cam_fw_ota_status
                    logger.debug(f"Status before OTA is: {self._previous_status}")

                    await publish_configure(
                        ephemeral_agent,
                        OnWireProtocol.EVP1,
                        "backdoor-EA_Main",
                        "placeholder",
                        payload,
                    )

                    task_status.started()
                    await self._finished.wait()
                    # From this point on, the OTA process is stimulated
                    # with the messages processed at on_message_received()

            if self._timeout_scope.cancelled_caught:
                self.notify_fn("Firmware update timed out!")
                await self._transition_out()

            self._http.delist_file(tmp_firmware)

    async def on_message_received(self, message: MQTTEvent) -> None:
        await super().on_message_received(message)
        if self._previous_report == self._props_report:
            return
        self._timeout_scope.deadline += self._timeout_secs

        ota_status = self._props_report.cam_fw_ota_status
        if ota_status and ota_status != self._previous_status:
            self._props_report.cam_fw_ota_status = ota_status

            logger.debug(f"OTA status is {ota_status}")
            if progress_update_checkpoint(ota_status, True, self.notify_fn):
                logger.debug("Finished updating!")
                await self._transition_out()

        self._previous_report = self._props_report.model_copy()
        self._previous_status = ota_status

    async def _transition_out(self) -> None:
        # Need to transit back to the ready-idle state
        from local_console.core.camera.states.v1.ready import ReadyCameraV1

        await self._transit_to(ReadyCameraV1(self._state_properties))
