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
from dataclasses import dataclass
from typing import Any

import trio
from local_console.clients.agent import Agent
from local_console.core.camera.enums import MQTTTopics
from local_console.core.commands.rpc_with_response import (
    DirectCommandResponseBody as V2DirectCommandResponse,
)
from local_console.core.commands.rpc_with_response import (
    DirectCommandStatus as V2DirectCommandStatus,
)
from local_console.utils.random import random_id
from pydantic import BaseModel
from pydantic import Field
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class DirectCommandResponse(BaseModel):
    module_instance: str = Field(alias="moduleInstance")
    response: str
    status: int = 0
    reqid: str


class DirectCommandRequestBody(BaseModel):
    method: str = Field(serialization_alias="moduleMethod")
    instance: str = Field(serialization_alias="moduleInstance")
    params: dict[str, Any]


class DirectCommandRequest(BaseModel):
    method: str = "ModuleMethodCall"
    params: DirectCommandRequestBody


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
            moduleInstance=rpc_argument.module_id,
            response="",
            status=0,
            reqid="",
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
                async with self._mqtt_client.client.messages() as mgen:
                    reqid = await self._send_rpc(rpc_argument)

                    logger.debug(f"Sent RPC, waiting for response: {reqid}")
                    async for msg in mgen:
                        if msg.topic.endswith(f"/{reqid}"):
                            try:
                                res = DirectCommandResponse.model_validate_json(
                                    msg.payload
                                )
                            except ValidationError:
                                res.response = msg.payload.decode()

                            res.reqid = reqid
                            cs.cancel()

        return res

    async def _send_rpc(self, rpc_argument: RPCArgument) -> str:
        reqid = random_id()

        payload_model = DirectCommandRequest(
            params=DirectCommandRequestBody(
                method=rpc_argument.method,
                instance=rpc_argument.module_id,
                params=rpc_argument.params,
            )
        )
        payload = payload_model.model_dump_json(by_alias=True)

        topic = f"v1/devices/me/rpc/request/{reqid}"
        logger.debug(f"RPC: topic={topic}, payload={payload}")
        await self._mqtt_client.publish(topic, payload)
        return reqid


async def run_rpc_with_response(
    mqtt_port: int,
    module_id: str,
    method: str,
    params: dict[str, Any],
    timeout: float = 60,
) -> DirectCommandResponse:
    rpc = RPCWithResponse(port=mqtt_port, timeout=timeout)
    return await rpc.run(
        RPCArgument(
            module_id=module_id,
            method=method,
            params=params,
        )
    )


def v1_rpc_response_to_v2(
    module_id: str, v1: DirectCommandResponse
) -> V2DirectCommandResponse:
    status = V2DirectCommandStatus.OK if v1.status == 0 else V2DirectCommandStatus.ERROR
    return V2DirectCommandResponse(
        response=v1.response,
        reqid=v1.reqid,
        status=status,
        errorMessage="",
    )
