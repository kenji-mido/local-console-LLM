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
from base64 import b64decode
from typing import Any

import trio
from local_console.core.camera.enums import MQTTTopics
from local_console.core.camera.states.base import BaseStateProperties
from local_console.core.camera.states.base import MQTTDriver
from local_console.core.camera.states.base import MQTTEvent
from local_console.core.camera.states.base import StateWithProperties
from local_console.core.camera.v2.components.device_info import DecodedDeviceManifest
from local_console.core.camera.v2.edge_system_common import EdgeSystemCommon
from local_console.core.helpers import check_attributes_request
from local_console.core.helpers import device_configure
from local_console.core.helpers import is_valid
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.core.schemas.schemas import DesiredDeviceConfig
from local_console.core.schemas.schemas import DeviceType
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.utils.timing import TimeoutBehavior
from pydantic import ValidationError

logger = logging.getLogger(__name__)


# MQTT constants
V1_EA_STATE_TOPIC = "state/backdoor-EA_Main/placeholder"
SYSINFO_TOPIC = "systemInfo"


class DisconnectedCamera(StateWithProperties):

    def __init__(self, base: BaseStateProperties) -> None:
        super().__init__(base)

    async def on_message_received(self, message: MQTTEvent) -> None:
        """
        Receiving a message means that the camera has connected, so
        immediately transit to the next state, and process this incoming
        message within that state.
        """
        next_state = IdentifyingCamera(self._state_properties)
        await self._transit_to(next_state)
        await next_state.on_message_received(message)

    async def enter(self, nursery: trio.Nursery) -> None:
        """Nothing to do"""

    async def exit(self) -> None:
        """Nothing to do"""


class ConnectedCameraState(StateWithProperties):
    """
    This state is meant to be inherited by other states that implement
    business logic upon the assumption that the device is connected.
    This implementation takes care of performing the connection timeout,
    that shall trigger a transition to the `DisconnectedCamera` state
    defined above.
    """

    CONNECTION_STATUS_TIMEOUT = 180

    def __init__(self, base: BaseStateProperties) -> None:
        super().__init__(base)

        # This timeout behavior takes care of updating the connectivity
        # status in case there are no incoming messages from the camera
        # for longer than the CONNECTION_STATUS_TIMEOUT threshold
        self._connection_alive_timeout = TimeoutBehavior(
            self.CONNECTION_STATUS_TIMEOUT,
            self._on_connection_timeout,
        )

    async def enter(self, nursery: trio.Nursery) -> None:
        self._connection_alive_timeout.spawn_in(nursery)

    async def exit(self) -> None:
        self._connection_alive_timeout.stop()

    async def on_message_received(self, message: MQTTEvent) -> None:
        logger.debug("Incoming on %s: %s", message.topic, message.payload)

        # This is a workaround to discriminate messages from the camera
        # apart from the MQTT loopback of messages published by Local Console.
        # This will be unnecessary when ThingsBoard's custom message routing is
        # used, instead of a plain MQTT broker like Mosquitto.
        sent_from_camera = True
        if message.topic == MQTTTopics.ATTRIBUTES.value and any(
            key.startswith("configuration/") for key in message.payload
        ):
            sent_from_camera = False
        if (
            message.topic == MQTTTopics.ATTRIBUTES.value
            and "desiredDeviceConfig" in message.payload
        ):
            sent_from_camera = False
        if message.topic == MQTTTopics.RPC_REQUESTS.value:
            sent_from_camera = False

        if sent_from_camera:
            self._connection_alive_timeout.tap()

        if await check_attributes_request(
            self._mqtt.client, message.topic, message.payload
        ):
            # attributes request handshake is performed at (re)connect
            # when reconnecting, multiple requests might be made
            return

    async def _on_connection_timeout(self) -> None:
        logger.debug("On connection timeout")
        self._connection_alive_timeout.stop()
        next_state = DisconnectedCamera(self._state_properties)
        await self._transit_to(next_state)


class IdentifyingCamera(ConnectedCameraState):

    V2_QUICK_REPORT_TIMEOUT_SECS: float = 2.0

    def __init__(self, base: BaseStateProperties) -> None:
        super().__init__(base)
        self._onwire_schema: OnWireProtocol | None = None
        self._v1_report = DeviceConfiguration.construct()
        self._v2_report = EdgeSystemCommon.construct()

        # As of v2 CamFW v1.0.4, it seems necessary to trigger the
        # emission of the telemetry message that contains the device
        # serial number, which is required here to fulfill identification.
        self._nursery: trio.Nursery | None = None
        self._v2_periodic_reports_timeout: TimeoutBehavior | None = None

    async def enter(self, nursery: trio.Nursery) -> None:
        await super().enter(nursery)
        self._nursery = nursery

    async def exit(self) -> None:
        await super().exit()

        if self._v2_periodic_reports_timeout:
            self._v2_periodic_reports_timeout.stop()
            # Set a slower report frequency to reduce loading on camera I/O:
            await set_periodic_reports_for_v2(
                self._mqtt, V2_PERIODIC_REPORT_TIMEOUT_SECS
            )

    async def on_message_received(self, message: MQTTEvent) -> None:
        await super().on_message_received(message)

        # TODO: This method receives OS and ARCH but it is not checking
        #       compatibility of the combination.
        #       When the right mechanism is available to stop/crash
        #       gracefully this check should be added.
        if message.topic == MQTTTopics.ATTRIBUTES.value:
            self._v1_detect_from_attrs(message.payload)
            await self._v2_detect_from_attrs(message.payload)

        elif message.topic == MQTTTopics.TELEMETRY.value:
            self._v1_detect_from_telemetry(message.payload)
            self._v2_detect_from_telemetry(message.payload)

        if self._state_properties.device_type != DeviceType.UNKNOWN:
            if self._onwire_schema == OnWireProtocol.EVP1 and (
                is_valid(self._v1_report) or not self._props_report.is_empty()
            ):
                from local_console.core.camera.states.v1.ready import ReadyCameraV1

                ready_state = ReadyCameraV1(self._state_properties, self._v1_report)
                await self._transit_to(ready_state)
                # Preventive countermeasure
                await ready_state._rpc_stop_streaming()

            elif self._onwire_schema == OnWireProtocol.EVP2 and (
                is_valid(self._v2_report) or not self._props_report.is_empty()
            ):
                from local_console.core.camera.states.v2.ready import ReadyCameraV2

                assert self._v2_report
                await self._transit_to(
                    ReadyCameraV2(
                        self._state_properties,
                        self._v2_report,
                    )
                )

    def _v1_detect_from_attrs(self, payload: dict[str, Any]) -> None:
        try:
            decoded = json.loads(b64decode(payload[V1_EA_STATE_TOPIC]))
            self._v1_report = DeviceConfiguration.model_validate(decoded)
        except (UnicodeDecodeError, ValidationError, KeyError):
            pass

        try:
            if SYSINFO_TOPIC not in payload:
                return
            sys_info_obj = payload[SYSINFO_TOPIC]
            self._onwire_schema = OnWireProtocol.EVP1
            if "protocolVersion" in sys_info_obj:
                self._onwire_schema = OnWireProtocol(sys_info_obj["protocolVersion"])

        except ValidationError:
            pass

    async def _v2_detect_from_attrs(self, payload: dict[str, Any]) -> None:
        try:
            v2_update = EdgeSystemCommon(**payload)
            non_null = v2_update.model_dump(exclude_none=True)
            for key, value in non_null.items():
                setattr(self._v2_report, key, value)

            if (
                self._v2_report.system_info
                and self._v2_report.system_info.protocolVersion
            ):
                self._onwire_schema = self._v2_report.system_info.protocolVersion

            if self._v2_periodic_reports_timeout:
                self._v2_periodic_reports_timeout.tap()
            else:
                assert self._nursery
                self._v2_periodic_reports_timeout = TimeoutBehavior(
                    2, self._v2_set_periodic_reports
                )
                self._v2_periodic_reports_timeout.spawn_in(self._nursery)
                await self._v2_set_periodic_reports()

            if (
                self._v2_report.system_info
                and self._v2_report.system_info.os != "NuttX"
            ):
                self._state_properties.device_type = DeviceType.RPi

            if self._v2_report.device_info:
                device_manifest = DecodedDeviceManifest.from_device_manifest(
                    self._v2_report.device_info.device_manifest
                )

                self._state_properties.device_type = DeviceType.from_value(
                    value=device_manifest.AITRIOSCertUUID
                )

        except ValidationError:
            pass

    def _v1_detect_from_telemetry(self, payload: dict[str, Any]) -> None:
        try:
            self._state_properties.device_type = DeviceType.from_value(
                value=payload["values"]["backdoor-EA_Main/EventLog"]["DeviceID"]
            )
        except Exception:
            pass

    def _v2_detect_from_telemetry(self, payload: dict[str, Any]) -> None:
        if "$system/event_log" in payload and "serial" in payload["$system/event_log"]:
            self._state_properties.device_type = DeviceType.from_value(
                value=payload["$system/event_log"]["serial"]
            )

    async def _v2_set_periodic_reports(self) -> None:
        await set_periodic_reports_for_v2(self._mqtt, self.V2_QUICK_REPORT_TIMEOUT_SECS)


V2_PERIODIC_REPORT_TIMEOUT_SECS: float = 6.0


async def set_periodic_reports_for_v2(
    mqtt_drv: MQTTDriver, timeout_secs: float
) -> None:
    """
    Configure the device to emit status reports twice
    as often as the timeout expiration, to avoid that
    random deviations in reporting periodicity make the timer
    to expire unnecessarily.
    """
    timeout = int(0.5 * timeout_secs)
    await device_configure(
        mqtt_drv.client,
        OnWireProtocol.EVP2,
        DesiredDeviceConfig(
            reportStatusIntervalMax=timeout,
            reportStatusIntervalMin=min(timeout, 1),
        ),
    )
