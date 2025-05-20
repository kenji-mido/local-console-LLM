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
from dataclasses import dataclass
from typing import Any

import trio
from local_console.clients.agent import Agent
from local_console.core.camera.enums import MQTTTopics
from local_console.utils.enums import StrEnum
from local_console.utils.random import random_id
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

logger = logging.getLogger(__name__)


class DirectCommandStatus(StrEnum):
    OK = "ok"
    ERROR = "error"


class DirectCommandResponseBody(BaseModel):
    response: str
    reqid: str
    status: DirectCommandStatus
    errorMessage: str = ""


class DirectCommandResponse(BaseModel):
    direct_command_response: DirectCommandResponseBody = Field(
        alias="direct-command-response",
    )

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def empty_ok(cls) -> "DirectCommandResponse":
        return cls(
            direct_command_response=DirectCommandResponseBody(
                response="",
                reqid="",
                status=DirectCommandStatus.OK,
            )
        )


class DirectCommandRequestBody(BaseModel):
    reqid: str
    method: str
    instance: str
    params: str


class DirectCommandRequest(BaseModel):
    # Using `serialization_alias` to define it through attribute name.
    direct_command_request: DirectCommandRequestBody = Field(
        serialization_alias="direct-command-request",
    )


class DirectCommandRequestRoot(BaseModel):
    method: str = "ModuleMethodCall"
    params: DirectCommandRequest


@dataclass
class RPCArgument:
    module_id: str
    method: str
    params: dict[str, Any]


class RPCWithResponse:
    def __init__(self, port: int, timeout: float) -> None:
        self._mqtt_client = Agent(port)
        self._timeout = timeout

    async def run(self, rpc_argument: RPCArgument) -> DirectCommandResponse:
        res = DirectCommandResponse(
            **{
                "direct-command-response": DirectCommandResponseBody(
                    response="",
                    reqid="",
                    status=DirectCommandStatus.ERROR,
                    errorMessage="Timeout",
                )
            }
        )

        with trio.move_on_after(self._timeout) as cs:
            # Open scope before sending RPC to ensure response is caught
            async with (
                self._mqtt_client.mqtt_scope(
                    [
                        MQTTTopics.RPC_RESPONSES.value,
                    ]
                ),
            ):
                assert self._mqtt_client.client
                reqid = await self._send_rpc(rpc_argument)
                logger.debug(f"Sent RPC, waiting for response: {reqid}")

                async with self._mqtt_client.client.messages() as mgen:
                    async for msg in mgen:
                        if msg.topic.endswith(f"/{reqid}"):
                            res = DirectCommandResponse.model_validate_json(
                                msg.payload.decode()
                            )
                            # Workaround to cancel generator from `trio_async_generator`
                            cs.cancel()

        return res

    async def _send_rpc(self, rpc_argument: RPCArgument) -> str:
        reqid = random_id()

        payload_model = DirectCommandRequestRoot(
            params=DirectCommandRequest(
                direct_command_request=DirectCommandRequestBody(
                    reqid=reqid,
                    method=rpc_argument.method,
                    instance=rpc_argument.module_id,
                    params=json.dumps(rpc_argument.params),
                )
            )
        )
        payload = payload_model.model_dump_json(by_alias=True)

        topic = f"v1/devices/me/rpc/request/{reqid}"
        logger.debug(f"RPC: topic={topic}, payload={payload}")
        await self._mqtt_client.publish(topic, payload)
        return reqid


async def run_rpc_with_response(
    port: int,
    module_id: str,
    method: str,
    params: dict[str, Any],
    timeout: float = 60,
) -> DirectCommandResponse:
    """
    v2 version of run_rpc_with_response
    """
    rpc = RPCWithResponse(port=port, timeout=timeout)  # type: ignore
    return await rpc.run(
        RPCArgument(
            module_id=module_id,
            method=method,
            params=params,
        )
    )
