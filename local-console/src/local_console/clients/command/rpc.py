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

from local_console.clients.command.base_command import CommandClient
from local_console.clients.command.base_command import MqttCommand
from local_console.clients.command.rpc_base import RPCArgument
from local_console.clients.command.rpc_base import RPCId
from local_console.clients.command.rpc_injector import RPCInjector
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.utils.random import random_id

logger = logging.getLogger(__name__)


async def call_rpc(client: CommandClient, payload: str, reqid: str) -> RPCId:
    topic = f"v1/devices/me/rpc/request/{reqid}"
    logger.debug(f"Publishing to {topic} rpc response")
    await client.publish(topic, payload)
    return RPCId(response_id=reqid)


class RPCEVP1(MqttCommand[RPCArgument, RPCId]):
    def __init__(self, client: CommandClient) -> None:
        super().__init__(client)

    async def run(self, input: RPCArgument) -> RPCId:
        assert input.onwire_schema == OnWireProtocol.EVP1
        # Following the implementation at:
        # https://github.com/midokura/wedge-agent/blob/fa3d4840c37978938084cbc70612fdb8ea8dbf9f/src/libwedge-agent/hub/tb/tb.c#L179
        # https://github.com/midokura/wedge-agent/blob/fa3d4840c37978938084cbc70612fdb8ea8dbf9f/src/libwedge-agent/direct_command.c#L158
        # https://github.com/midokura/evp-onwire-schema/blob/1164987a620f34e142869f3979ca63b186c0a061/schema/directcommandrequest/direct-command-request.example.json#L2
        evp1_body = {
            "moduleMethod": input.method,
            "moduleInstance": input.instance_id,
            "params": input.params,
        }
        payload = json.dumps(
            {
                "method": "ModuleMethodCall",
                "params": evp1_body,
            }
        )
        return await call_rpc(self.client, payload, random_id())


class RPCEVP2(MqttCommand[RPCArgument, RPCId]):
    def __init__(self, client: CommandClient) -> None:
        super().__init__(client)

    async def run(self, input: RPCArgument) -> RPCId:
        assert input.onwire_schema == OnWireProtocol.EVP2
        reqid = random_id()
        # Following the implementation at:
        # https://github.com/midokura/wedge-agent/blob/fa3d4840c37978938084cbc70612fdb8ea8dbf9f/src/libwedge-agent/hub/tb/tb.c#L218
        # https://github.com/midokura/wedge-agent/blob/fa3d4840c37978938084cbc70612fdb8ea8dbf9f/src/libwedge-agent/direct_command.c#L206
        # https://github.com/midokura/evp-onwire-schema/blob/9a0a861a6518681ceda5749890d4322a56dfbc3e/schema/direct-command-request.example.json#L2
        evp2_body = {
            "direct-command-request": {
                "reqid": reqid,
                "method": input.method,
                "instance": input.instance_id,
                "params": json.dumps(input.params),
            }
        }
        payload = json.dumps(
            {
                "method": "ModuleMethodCall",
                "params": evp2_body,
            }
        )
        return await call_rpc(self.client, payload, reqid)


class RPC(MqttCommand[RPCArgument, RPCId]):
    def __init__(self, client: CommandClient, injector: RPCInjector) -> None:
        super().__init__(client)
        self._injector = injector

    def _executor_factory(self, input: RPCArgument) -> MqttCommand[RPCArgument, RPCId]:
        if input.onwire_schema == OnWireProtocol.EVP1:
            return RPCEVP1(self.client)
        elif input.onwire_schema == OnWireProtocol.EVP2:
            return RPCEVP2(self.client)
        else:
            raise NotImplementedError(f"Could not manage {input.onwire_schema} type")

    async def run(self, input: RPCArgument) -> RPCId:
        executor: MqttCommand[RPCArgument, RPCId] = self._executor_factory(input)
        enriched = self._injector.inject(input)
        return await executor.run(enriched)
