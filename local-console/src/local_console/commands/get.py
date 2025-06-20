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
from typing import Callable
from typing import Optional

import trio
import typer
from local_console.clients.agent import Agent
from local_console.commands.utils import find_device_config
from local_console.core.camera.enums import MQTTTopics
from local_console.core.helpers import read_only_loop
from local_console.plugin import PluginBase

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="get", help="Command to get information of the running edge application"
)


@app.command(help="Get the status of deployment")
def deployment(
    device: Annotated[
        Optional[str],
        typer.Option(
            "--device",
            "-d",
            help="The name of the device to listen to deployment updates.",
        ),
    ] = None,
    port: Annotated[
        Optional[int],
        typer.Option(
            help="An alternative to --device, using the port to identify the device instead of its name. Ignored if the --device option is specified."
        ),
    ] = None,
) -> None:
    device_config = find_device_config(device, port)
    agent = Agent(device_config.mqtt.port)
    read_only_loop(
        agent,
        subs_topics=[MQTTTopics.ATTRIBUTES.value],
        message_task=on_message_print_payload,
    )


async def on_message_print_payload(cs: trio.CancelScope, agent: Agent) -> None:
    assert agent.client is not None
    async with agent.client.messages() as mgen:
        async for msg in mgen:
            payload = json.loads(msg.payload.decode())
            if payload:
                print(payload, flush=True)
            else:
                logger.debug("Empty message arrived")


@app.command(help="Get telemetries being sent from the application")
def telemetry(
    device: Annotated[
        Optional[str],
        typer.Option(
            "--device",
            "-d",
            help="The name of the device for which to display telemetries.",
        ),
    ] = None,
    port: Annotated[
        Optional[int],
        typer.Option(
            help="An alternative to --device, using the port to identify the device instead of its name. Ignored if the --device option is specified."
        ),
    ] = None,
) -> None:
    device_config = find_device_config(device, port)
    agent = Agent(device_config.mqtt.port)
    read_only_loop(
        agent,
        subs_topics=[MQTTTopics.TELEMETRY.value],
        message_task=on_message_telemetry,
    )


async def on_message_telemetry(cs: trio.CancelScope, agent: Agent) -> None:
    assert agent.client is not None
    async with agent.client.messages() as mgen:
        async for msg in mgen:
            payload = json.loads(msg.payload.decode())
            if payload:
                to_print = {
                    key: val for key, val in payload.items() if "device/log" not in key
                }
                print(to_print, flush=True)


@app.command(help="Get the status of an instance module")
def instance(
    instance_id: Annotated[
        str,
        typer.Argument(help="Target instance of the RPC"),
    ],
    device: Annotated[
        Optional[str],
        typer.Option(
            "--device",
            "-d",
            help="The name of the device to listen to instance updates.",
        ),
    ] = None,
    port: Annotated[
        Optional[int],
        typer.Option(
            help="An alternative to --device, using the port to identify the device instead of its name. Ignored if the --device option is specified."
        ),
    ] = None,
) -> None:
    device_config = find_device_config(device, port)
    agent = Agent(device_config.mqtt.port)
    read_only_loop(
        agent,
        subs_topics=[MQTTTopics.ATTRIBUTES.value],
        message_task=on_message_instance(instance_id),
    )


def on_message_instance(instance_id: str) -> Callable:
    async def __task(cs: trio.CancelScope, agent: Agent) -> None:
        assert agent.client is not None
        async with agent.client.messages() as mgen:
            async for msg in mgen:
                payload = json.loads(msg.payload.decode())
                if (
                    "deploymentStatus" not in payload
                    or "instances" not in payload["deploymentStatus"]
                ):
                    continue

                instances = payload["deploymentStatus"]["instances"]
                if instance_id in instances.keys():
                    print(instances[instance_id])
                else:
                    logger.warning(
                        f"Module instance not found. The available module instances are {list(instances.keys())}"
                    )
                    cs.cancel()

    return __task


class GetCommand(PluginBase):
    implementer = app
