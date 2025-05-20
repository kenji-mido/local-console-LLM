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
import signal
import sys
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
import trio
from fastapi import FastAPI
from local_console.commands.server import LISTEN_PORT
from local_console.commands.server import server_main
from local_console.commands.server import ServerCommand
from local_console.commands.server import shutdown_trigger
from local_console.commands.server import wait_for_signals
from local_console.commands.server import wait_over_stdin
from typer.testing import CliRunner

runner = CliRunner()


def test_server_call_fast_api():
    with (
        patch("trio.run") as mock_trio,
        patch(
            "local_console.commands.server.server_main", return_value=0
        ) as mock_server,
    ):
        cmd = ServerCommand()
        runner.invoke(cmd.implementer, [])

        mock_trio.assert_called_once_with(mock_server)


@pytest.mark.trio
async def test_server_main_happy_path(nursery):

    with (
        patch("local_console.commands.server.generate_server", return_value=FastAPI()),
        patch("local_console.commands.server.shutdown_trigger") as mock_trigger,
    ):
        retcode = await server_main()
        assert retcode == 0
        mock_trigger.assert_awaited_once()


@pytest.mark.trio
async def test_server_main_config_binding(nursery):
    with (
        patch("local_console.commands.server.Config") as mock_config,
        patch("local_console.commands.server.serve"),
        patch("local_console.commands.server.shutdown_trigger"),
        patch("local_console.commands.server.is_port_open", return_value=False),
    ):
        retcode = await server_main()
        assert retcode == 0

        assert mock_config.return_value.bind == [f"0.0.0.0:{LISTEN_PORT}"]


@pytest.mark.trio
async def test_server_main_some_server_error(nursery, caplog):

    mock_server = AsyncMock()
    mock_server.return_value = AsyncMock(side_effect=IOError())
    with (
        patch(
            "local_console.commands.server.generate_server", return_value=mock_server
        ),
        patch("local_console.commands.server.shutdown_trigger"),
    ):
        retcode = await server_main()
        assert retcode == 1
        assert "Cannot start API server due to" in caplog.text


@pytest.mark.trio
async def test_error_when_listener_port_is_taken(nursery):
    with (
        patch("local_console.commands.server.generate_server", return_value=FastAPI()),
        patch("local_console.commands.server.report_exception") as mock_excproc,
    ):
        # This is some other process bound to the port our server means to bind to.
        async def dummy_handler(stream: trio.SocketStream) -> None:
            await stream.send_all(b"")

        await nursery.start(trio.serve_tcp, dummy_handler, LISTEN_PORT)

        # Now attempt to run the server, which shall fail
        retcode = await server_main()
        assert retcode == 1
        mock_excproc.assert_called_once()
        assert mock_excproc.call_args[0][0].errno == 98
        assert mock_excproc.call_args[0][0].strerror == "Address already in use"


@pytest.mark.trio
async def test_wait_over_stdin_shutdown_command():
    finish_event = trio.Event()
    with patch("sys.stdin") as mock_stdin:
        mock_stdin.readline = MagicMock(return_value="shutdown\n")
        await wait_over_stdin(finish_event)
    assert finish_event.is_set()


@pytest.mark.trio
async def test_wait_over_stdin_no_trigger(nursery, autojump_clock):
    finish_event = trio.Event()
    with patch("sys.stdin") as mock_stdin:
        mock_stdin.readline = MagicMock(side_effect=["hello\n", "world\n"])
        # https://trio.readthedocs.io/en/latest/reference-core.html#trio.Nursery.start
        await nursery.start(wait_over_stdin, finish_event)
        with trio.move_on_after(0.5):
            await finish_event.wait()
        assert not finish_event.is_set()


@pytest.mark.trio
@pytest.mark.skipif(
    sys.platform == "win32", reason="To test signal handling on Windows is futile"
)
async def test_wait_for_signals():
    finish_event = trio.Event()

    async def mock_signal_aiter():
        yield signal.SIGINT

    mock_signal_receiver = MagicMock()
    mock_signal_receiver.__enter__.return_value = mock_signal_aiter()
    with patch("trio.open_signal_receiver", return_value=mock_signal_receiver):
        await wait_for_signals(finish_event)

    assert finish_event.is_set()


@pytest.mark.trio
async def test_shutdown_trigger_over_stdin():
    with (
        patch("local_console.commands.server.wait_over_stdin") as mock_wait_over_stdin,
        patch(
            "local_console.commands.server.wait_for_signals"
        ) as mock_wait_for_signals,
    ):

        async def mock_wait_over_stdin_func(finish_event: trio.Event) -> None:
            finish_event.set()

        async def mock_wait_for_signals_func(finish_event: trio.Event) -> None:
            # No signal will ever be sent by the OS
            await trio.sleep_forever()

        mock_wait_over_stdin.side_effect = mock_wait_over_stdin_func
        mock_wait_for_signals.side_effect = mock_wait_for_signals_func
        with trio.move_on_after(1):
            await shutdown_trigger()
        mock_wait_over_stdin.assert_called_once()


@pytest.mark.trio
@pytest.mark.skipif(
    sys.platform == "win32", reason="To test signal handling on Windows is futile"
)
async def test_shutdown_trigger_over_signals():
    with (
        patch("local_console.commands.server.wait_over_stdin") as mock_wait_over_stdin,
        patch(
            "local_console.commands.server.wait_for_signals"
        ) as mock_wait_for_signals,
    ):

        async def mock_wait_for_signals_func(finish_event: trio.Event) -> None:
            finish_event.set()

        async def mock_wait_over_stdin_func(finish_event: trio.Event) -> None:
            # No input over stdin will ever be received
            await trio.sleep_forever()

        mock_wait_for_signals.side_effect = mock_wait_for_signals_func
        mock_wait_over_stdin.side_effect = mock_wait_over_stdin_func
        with trio.move_on_after(1):
            await shutdown_trigger()
        mock_wait_for_signals.assert_called_once()


@pytest.mark.trio
async def test_shutdown_trigger_without_trigger(autojump_clock):

    finish_event = trio.Event()
    with (
        patch("trio.Event", return_value=finish_event),
        patch("local_console.commands.server.wait_over_stdin") as mock_wait_over_stdin,
        patch(
            "local_console.commands.server.wait_for_signals"
        ) as mock_wait_for_signals,
    ):

        async def mock_wait_for_signals_func(finish_event: trio.Event) -> None:
            # No signal will ever be sent by the OS
            await trio.sleep_forever()

        async def mock_wait_over_stdin_func(finish_event: trio.Event) -> None:
            # No input over stdin will ever be received
            await trio.sleep_forever()

        mock_wait_for_signals.side_effect = mock_wait_for_signals_func
        mock_wait_over_stdin.side_effect = mock_wait_over_stdin_func

        # Wait for an inordinate amount of time...
        with trio.move_on_after(1e9):
            await shutdown_trigger()

        # ... and see that the event was not fired off
        assert not finish_event.is_set()
