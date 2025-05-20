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
from typing import Annotated
from typing import Optional
from unittest.mock import patch

import trio
import typer
from local_console.commands.utils import dummy_props_for_state
from local_console.commands.utils import find_device_config
from local_console.core.camera.states.v1.common import ConnectedCameraStateV1
from local_console.core.camera.states.v2.common import ConnectedCameraStateV2
from local_console.core.schemas.schemas import DeviceConnection
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.plugin import PluginBase

app = typer.Typer()

logger = logging.getLogger(__name__)


@app.command(help="Command to send RPC to a module instance")
def rpc(
    instance_id: Annotated[
        str,
        typer.Argument(help="Target instance of the RPC"),
    ],
    method: Annotated[
        str,
        typer.Argument(help="Method of the RPC"),
    ],
    params: Annotated[
        str,
        typer.Argument(help="JSON representing the parameters"),
    ],
    device: Annotated[
        Optional[str],
        typer.Option(
            "--device",
            "-d",
            help="The name of the device to which the RPC command will be sent.",
        ),
    ] = None,
    port: Annotated[
        Optional[int],
        typer.Option(help="TCP port on which the MQTT broker is listening"),
    ] = None,
) -> None:
    config = find_device_config(device, port)
    try:
        trio.run(rpc_task, instance_id, method, params, config)
    except ConnectionError:
        logger.error(f"Could not send command {method} to device {instance_id}")
        raise typer.Exit(code=1)


async def rpc_task(
    instance_id: str,
    method: str,
    params: str,
    config: DeviceConnection,
) -> None:
    schema = config.onwire_schema

    # No need to spawn a broker
    with patch("local_console.core.camera.states.base.spawn_broker"):
        state_props = dummy_props_for_state(config)
        mqtt_driver = state_props.mqtt_drv

        state = (
            ConnectedCameraStateV1(state_props)
            if schema == OnWireProtocol.EVP1
            else ConnectedCameraStateV2(state_props)
        )
        try:
            async with trio.open_nursery() as nursery:

                mqtt_driver.set_handler(state.on_message_received)

                await nursery.start(mqtt_driver.setup)
                await state.enter(nursery)

                assert hasattr(
                    state, "_push_rpc"
                )  # due to the different returned type, mypy doesn't acknowledge the shared method
                response = await state._push_rpc(
                    instance_id, method, json.loads(params), {}
                )
                if response:
                    logger.info(f"Got reply: {response}")

                nursery.cancel_scope.cancel()
        except* KeyboardInterrupt:
            pass


class RPCCommand(PluginBase):
    implementer = app
