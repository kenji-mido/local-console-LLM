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
import base64
import binascii
import logging
from collections.abc import Awaitable
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
from typing import Callable

import trio
from local_console.clients.command.base_command import CommandResponse
from local_console.clients.command.base_command import MqttCommand
from local_console.clients.command.rpc import RPC
from local_console.clients.command.rpc import RPCArgument
from local_console.clients.command.rpc import RPCId
from local_console.clients.command.rpc_injector import ChainedRPCInjector
from local_console.clients.command.rpc_injector import RPCInjector
from local_console.clients.command.rpc_injector import StartStreamingInjector
from local_console.clients.command.rpc_injector import StartStreamingProvider
from local_console.core.camera.mixin_mqtt import MQTTEvent
from local_console.core.camera.state import CameraState
from local_console.core.error.base import InternalException
from local_console.core.error.code import ErrorCodes
from local_console.core.schemas.edge_cloud_if_v1 import StartUploadInferenceData
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.utils.tracking import TrackingVariable
from local_console.utils.trio import TimeoutConfig


logger = logging.getLogger(__name__)


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")[:-3]


def camera_injector(camera_state: CameraState) -> RPCInjector:
    class ProxyStartStreamingProvider(StartStreamingProvider):
        def __init__(self, state: CameraState) -> None:
            self._camera_state = state

        def streaming_rpc_start_content(self) -> StartUploadInferenceData:
            return self._camera_state.streaming_rpc_start_content()

    return ChainedRPCInjector(
        [StartStreamingInjector(ProxyStartStreamingProvider(camera_state))]
    )


class RPCResponse(CommandResponse):
    topic: str
    payload: dict[str, Any]


class RPCWithResponse(MqttCommand[RPCArgument, RPCResponse]):
    def __init__(
        self,
        camera_state: CameraState,
        interval_in_seconds: float = 0.2,
        sleeper: Callable[[float], Awaitable[None]] = trio.sleep,
        max_time_waiting_seconds: float = 60,
    ) -> None:
        if not camera_state.mqtt_client:
            raise InternalException(
                ErrorCodes.INTERNAL_DEVICE_RPC_MISSING_CLIENT,
                "Internal error. Could connect to the camera.",
            )
        super().__init__(camera_state.mqtt_client)
        injector = camera_injector(camera_state)
        self.rpc = RPC(camera_state.mqtt_client, injector)
        self.timeout = TimeoutConfig(
            pollin_interval_in_seconds=interval_in_seconds,
            timeout_in_seconds=max_time_waiting_seconds,
        )
        self.sleeper = sleeper
        self.response: MQTTEvent | None = None
        self.sent_id: RPCId | None = None
        self._image_path = camera_state.image_dir_path.value

    def _direct_image(self, event: MQTTEvent) -> None:
        if not isinstance(self._image_path, Path):
            logger.error(f"Invalid path to store images: {self._image_path}")
            return

        if (
            event.topic.startswith("v1/devices/me/rpc/response/")
            and "response" in event.payload
            and "Image" in event.payload["response"]
        ):
            file = self._image_path / f"{timestamp()}.jpg"
            try:
                file.write_bytes(
                    base64.b64decode(event.payload["response"]["Image"].encode())
                )
            except binascii.Error as e:
                logger.info("Error decoding image", exc_info=e)

    def _process(self, event: MQTTEvent) -> None:
        self.response = event
        self._direct_image(event)

    async def run(self, input: RPCArgument) -> RPCResponse:
        self.sent_id = await self.rpc.run(input)
        logger.debug(
            f"Rpc sended. It will wait for response for {self.sent_id.response_id}"
        )
        for _ in range(self.timeout.num_of_iterations()):
            if self.response:
                return RPCResponse(**self.response.model_dump())
            logger.debug(
                f"Sleep for {self.timeout.pollin_interval_in_seconds} seconds waiting for response"
            )
            await self.sleeper(self.timeout.pollin_interval_in_seconds)
        raise TimeoutError(
            f"Response for RPC did not arrive in {self.timeout.timeout_in_seconds} seconds"
        )

    def listener(self) -> Callable[[MQTTEvent | None, MQTTEvent | None], None]:
        def process_responses(new: MQTTEvent | None, _: MQTTEvent | None) -> None:
            if (
                new
                and self.sent_id
                and new.topic.endswith(f"/{self.sent_id.response_id}")
            ):
                logger.debug(f"Response for {self.sent_id.response_id} has arribed")
                self._process(new)
            else:
                logger.debug(
                    f"Discarded message with topic {new.topic if new else 'None'} as response for {self.sent_id.response_id if self.sent_id else 'None'}"
                )

        return process_responses


async def run_rpc_with_response(
    camera_state: CameraState,
    tracker: TrackingVariable[MQTTEvent],
    command_name: str,
    parameters: dict[str, Any],
    schema: OnWireProtocol,
) -> RPCResponse:

    command = RPCWithResponse(camera_state)
    response_waiter = command.listener()
    tracker.subscribe(response_waiter)
    try:
        result = await command.run(
            RPCArgument(
                onwire_schema=schema,
                instance_id="backdoor-EA_Main",
                method=command_name,
                params=parameters,
            )
        )
        return result
    except Exception as e:
        raise e
    finally:
        tracker.unsubscribe(response_waiter)
