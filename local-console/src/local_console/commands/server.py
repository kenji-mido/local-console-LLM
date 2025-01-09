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
import errno
import logging
import signal
import sys

import trio
import typer
from hypercorn.config import Config
from hypercorn.trio import serve
from local_console.fastapi.main import generate_server
from local_console.plugin import PluginBase
from local_console.utils.local_network import is_port_open
from trio_typing import TaskStatus

logger = logging.getLogger(__name__)

app = typer.Typer()


@app.command(
    "serve",
    help="Start UI in Web Server mode",
)
def run_serve() -> None:
    retcode = trio.run(server_main)
    raise typer.Exit(code=retcode)


LISTEN_PORT: int = 8000


async def server_main() -> int:
    retcode: int = 1

    config = Config()
    config.bind = [f"localhost:{LISTEN_PORT}"]
    config.accesslog = logging.getLogger("hypercorn.access")

    try:
        if is_port_open(LISTEN_PORT):
            raise OSError(errno.EADDRINUSE, "Address already in use")

        server = generate_server()
        await serve(server, config, shutdown_trigger=shutdown_trigger)
        retcode = 0
    except* Exception as excgroups:
        for group_or_exc in excgroups.exceptions:
            if isinstance(group_or_exc, ExceptionGroup):
                for exc in group_or_exc.exceptions:
                    report_exception(exc)
            else:
                report_exception(group_or_exc)

    return retcode


def report_exception(exc: Exception) -> None:
    if isinstance(exc, OSError) and exc.errno == errno.EADDRINUSE:
        logger.error(
            f"Cannot start API server since port {LISTEN_PORT} is used by another process."
        )
    else:
        logger.error("Cannot start API server due to:", exc_info=exc)


async def shutdown_trigger() -> None:

    finish = trio.Event()
    async with trio.open_nursery() as nursery:
        # Task to wait for signals on *nix
        if sys.platform != "win32":
            nursery.start_soon(wait_for_signals, finish)

        # Task to wait for the 'shutdown' command
        nursery.start_soon(wait_over_stdin, finish)

        await finish.wait()
        nursery.cancel_scope.cancel()


async def wait_for_signals(finish_event: trio.Event) -> None:
    with trio.open_signal_receiver(signal.SIGTERM, signal.SIGINT) as signal_aiter:
        async for signum in signal_aiter:
            logger.debug(f"Received signal {signum}, shutting down.")
            finish_event.set()
            break


async def wait_over_stdin(
    finish_event: trio.Event, task_status: TaskStatus = trio.TASK_STATUS_IGNORED
) -> None:
    # task_status is used to let trio know the background task has started
    # https://pytest-trio.readthedocs.io/en/latest/quickstart.html#running-a-background-server-from-a-fixture
    task_status.started()
    while True:
        # The mypy ignore of next line is due to https://github.com/python-trio/trio-typing/pull/96
        line = await trio.to_thread.run_sync(sys.stdin.readline, abandon_on_cancel=True)  # type: ignore[call-overload]
        if line.strip() == "shutdown":
            logger.debug("Received shutdown command over stdin")
            finish_event.set()
            break


class ServerCommand(PluginBase):
    implementer = app
