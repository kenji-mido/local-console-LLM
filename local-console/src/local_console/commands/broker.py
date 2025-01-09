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
import signal
from typing import Annotated

import trio
import typer
from local_console.core.config import config_obj
from local_console.core.schemas.schemas import DeviceConnection
from local_console.plugin import PluginBase
from local_console.servers.broker import BrokerException
from local_console.servers.broker import spawn_broker
from trio import Event
from trio import open_nursery

app = typer.Typer()

logger = logging.getLogger(__name__)


@app.command(
    help="Command to start a MQTT broker. It will fail if there is already a broker listening in the port specified in config"
)
def broker(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Starts the broker in verbose mode"),
    ] = False,
) -> None:
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    device_config = config_obj.get_active_device_config()
    retcode = trio.run(broker_task, device_config, verbose)
    raise typer.Exit(code=retcode)


async def broker_task(config: DeviceConnection, verbose: bool) -> int:
    retcode: int = 1
    logger.setLevel(logging.INFO)
    finish = Event()
    try:
        async with (
            open_nursery() as nursery,
            spawn_broker(config.mqtt.port, nursery, verbose),
        ):
            logger.info(f"MQTT broker listening on port {config.mqtt.port}")

            nursery.start_soon(wait_for_signals, finish)
            await finish.wait()
            nursery.cancel_scope.cancel()
            retcode = 0

    except* Exception as exc_grp:
        for e in exc_grp.exceptions:
            if isinstance(e, BrokerException):
                logger.error(" ".join(str(e).splitlines()))

    return retcode


async def wait_for_signals(finish_event: trio.Event) -> None:
    with trio.open_signal_receiver(signal.SIGTERM, signal.SIGINT) as signal_aiter:
        async for signum in signal_aiter:
            logger.warning("Cancelled by the user")
            finish_event.set()
            break


class BrokerCommand(PluginBase):
    implementer = app
