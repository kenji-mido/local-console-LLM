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
import re
from datetime import datetime
from datetime import timezone
from os import error
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock
from unittest.mock import call
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
import trio
from local_console.clients.command.rpc import RPCArgument
from local_console.clients.command.rpc import RPCId
from local_console.clients.command.rpc_with_response import RPCResponse
from local_console.clients.command.rpc_with_response import RPCWithResponse
from local_console.clients.command.rpc_with_response import run_rpc_with_response
from local_console.clients.command.rpc_with_response import timestamp
from local_console.core.camera.mixin_mqtt import MQTTEvent
from local_console.core.camera.state import CameraState
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.utils.tracking import TrackingVariable
from local_console.utils.trio import EVENT_WAITING

from tests.fixtures.agent import mocked_agent
from tests.strategies.samplers.mqtt_message import MockMQTTMessage


class RPCTester:
    def __init__(self, rpc: RPCWithResponse, mocked_events: list[MQTTEvent]) -> None:
        self.rpc = rpc
        self.events = mocked_events
        self.listener = rpc.listener()

    async def sleeper(self, _: float):
        next_event = self.events.pop(0)
        ignored_event = next_event
        self.listener(next_event, ignored_event)

    def pending_events(self) -> int:
        return len(self.events)


@pytest.mark.trio
async def test_return_the_callback():
    with patch("local_console.clients.command.rpc_with_response.RPC") as raw_rpc:
        raw_rpc.return_value.run = AsyncMock(return_value=RPCId(response_id="1"))
        camera_state = MagicMock()

        rpc = RPCWithResponse(camera_state)
        input = RPCArgument(
            onwire_schema=OnWireProtocol.EVP1,
            instance_id="do",
            method="not",
            params={"matter": ""},
        )
        event = MQTTEvent(
            topic="v1/devices/me/rpc/response/1", payload={"image": "base64image"}
        )
        tester = RPCTester(rpc, mocked_events=[event])
        rpc.sleeper = tester.sleeper

        result = await rpc.run(input)
        raw_rpc.return_value.run.assert_awaited_once_with(input)
        assert result.topic == event.topic
        assert tester.pending_events() == 0


@pytest.mark.trio
async def test_discard_one_response():
    with patch("local_console.clients.command.rpc_with_response.RPC") as raw_rpc:
        raw_rpc.return_value.run = AsyncMock(return_value=RPCId(response_id="1"))

        rpc = RPCWithResponse(camera_state=MagicMock())
        input = RPCArgument(
            onwire_schema=OnWireProtocol.EVP1,
            instance_id="do",
            method="not",
            params={"matter": ""},
        )
        discarded_event = MQTTEvent(
            topic="v1/devices/me/rpc/response/2", payload={"image": "notTheExpected"}
        )
        event = MQTTEvent(
            topic="v1/devices/me/rpc/response/1", payload={"image": "base64image"}
        )
        tester = RPCTester(rpc, mocked_events=[discarded_event, event])
        rpc.sleeper = tester.sleeper

        result = await rpc.run(input)
        raw_rpc.return_value.run.assert_awaited_once_with(input)
        assert result.topic == event.topic
        assert tester.pending_events() == 0


@pytest.mark.trio
@patch("local_console.clients.command.rpc_with_response.RPCWithResponse")
async def test_rpc_call(command: MagicMock):
    response = RPCResponse(topic="topic", payload={"param": "value"})
    run_command = AsyncMock(return_value=response)
    state = MagicMock()
    tracker = MagicMock()
    command_name = "command"
    parameters = {"param": "value"}
    schema = OnWireProtocol.EVP1
    command.return_value.run = run_command

    await run_rpc_with_response(state, tracker, command_name, parameters, schema)

    run_command.assert_awaited_once()


@pytest.mark.trio
@patch("local_console.clients.command.rpc_with_response.RPCWithResponse")
async def test_call_subscribe_and_unsubscribe(command: MagicMock):
    error_running = Exception("could not run rpc")
    run_command = AsyncMock(side_effect=error_running)
    listener = MagicMock()
    command.return_value.listener.return_value = listener
    state = MagicMock()
    tracker = MagicMock()
    command_name = "command"
    parameters = {"param": "value"}
    schema = OnWireProtocol.EVP2
    command.return_value.run = run_command

    with pytest.raises(Exception) as error:
        await run_rpc_with_response(state, tracker, command_name, parameters, schema)

    assert error.value is error_running

    tracker.subscribe.assert_called_once_with(listener)
    tracker.unsubscribe.assert_called_once_with(listener)


@pytest.mark.trio
@pytest.mark.parametrize(
    "max, interval, num_calls",
    [
        (5.0, 1.0, 5),  # happy sample
        (60.0, 0.2, 300),  # defaults
        (7.8, 2.5, 3),  # Positive floats, expected truncation
        (10.0, 3.0, 3),  # Division with no decimal part
        (-7.8, 2.5, 1),  # Negative numerator, positive denominator
        (7.8, -2.5, 3),  # Positive numerator, negative denominator
        (-7.8, -2.5, 1),  # Negative numerator and denominator
        (0.0, 2.5, 1),  # Zero numerator
        (2.5, 7.8, 1),  # Result less than 1
        (5.0, 2.0, 2),  # Exact integer result
        (5.0, 0, 100),  # Division by zero
        (0.0, 0.0, 1),  # Zero divided by zero
    ],
)
async def test_timeout_error(max: float, interval: float, num_calls: int) -> None:
    with patch("local_console.clients.command.rpc_with_response.RPC") as raw_rpc:
        raw_rpc.return_value.run = AsyncMock(return_value=RPCId(response_id="1"))
        sleeper = AsyncMock()

        rpc = RPCWithResponse(
            camera_state=MagicMock(),
            interval_in_seconds=interval,
            max_time_waiting_seconds=max,
            sleeper=sleeper,
        )
        input = RPCArgument(
            onwire_schema=OnWireProtocol.EVP1,
            instance_id="do",
            method="not",
            params={"matter": ""},
        )
        with pytest.raises(TimeoutError) as error:
            await rpc.run(input)
        calls = [call(interval) for _ in range(num_calls)]
        sleeper.assert_has_awaits(calls=calls)
        assert str(error.value) == f"Response for RPC did not arrive in {max} seconds"


@pytest.mark.trio
@patch("local_console.clients.command.rpc_with_response.logger")
async def test_listener_log_success_message(mocked_log: MagicMock) -> None:
    rpc = RPCWithResponse(camera_state=MagicMock())
    rpc.sent_id = RPCId(response_id="1")
    new = MQTTEvent(topic="no/matter/what/1", payload={})
    rpc.listener()(new, None)

    mocked_log.debug.assert_called_once_with("Response for 1 has arribed")


@pytest.mark.trio
@patch("local_console.clients.command.rpc_with_response.logger")
async def test_listener_log_error_message(mocked_log: MagicMock) -> None:
    rpc = RPCWithResponse(camera_state=MagicMock())
    rpc.sent_id = RPCId(response_id="1")
    new = MQTTEvent(topic="no/matter/what/other", payload={})
    rpc.listener()(new, None)

    mocked_log.debug.assert_called_once_with(
        "Discarded message with topic no/matter/what/other as response for 1"
    )


@pytest.mark.trio
async def test_direct_image_is_stored() -> None:

    with mocked_agent() as agent, TemporaryDirectory(
        ignore_cleanup_errors=True
    ) as temporal:
        tmp = Path(temporal)
        state = CameraState(MagicMock(), MagicMock())
        state.mqtt_port.value = 1883
        state.mqtt_host.value = "localhost"
        state._onwire_schema = OnWireProtocol.EVP1
        state.image_dir_path.value = tmp / "images"
        agent.wait_for_messages = True
        async with trio.open_nursery() as nursery:
            # When we send an image
            async def direct_get_image() -> None:
                response = await run_rpc_with_response(
                    state,
                    state.rpc_response,
                    "DirectGetImage",
                    {},
                    OnWireProtocol.EVP1,
                )
                assert response.payload["response"]["Image"] == "RmFrZSBpbWFnZQ=="
                assert response.topic.startswith("v1/devices/me/rpc/response/")

            nursery.start_soon(state.startup, 1883)
            await EVENT_WAITING.wait_for(lambda: state.mqtt_client is not None)
            nursery.start_soon(direct_get_image)
            await EVENT_WAITING.wait_for(lambda: agent.agent.publish.await_count > 0)
            assert agent.agent.publish.await_count > 0
            requested_topic, _ignored = agent.agent.publish.await_args[0]
            reply_topic = requested_topic.replace("request", "response")
            payload = {
                "moduleInstance": "backdoor-EA_Main",
                "status": 0,
                "response": {"Result": "Succeeded", "Image": "RmFrZSBpbWFnZQ=="},
            }
            # And the device replies with an image
            msg = MockMQTTMessage(reply_topic, json.dumps(payload).encode("utf-8"))
            agent.send_messages([msg])

            def get_expected_file() -> Path | None:
                nonlocal tmp
                for file in (state.image_dir_path.value).iterdir():
                    if file.is_file() and file.suffix.endswith("jpg"):
                        return file
                return None

            # We expect the image to be stored in the images directory and base64 decoded
            await EVENT_WAITING.wait_for(lambda: get_expected_file() is not None)
            saved_image = get_expected_file()
            agent.wait_for_messages = False
            assert saved_image
            pattern = r"^\d{17}\.jpg$"
            assert re.match(pattern, saved_image.name)
            assert saved_image.read_text() == "Fake image"
        state.shutdown()


@pytest.mark.parametrize(
    "event",
    [
        MQTTEvent(topic="invalid/topic", payload={}),
        MQTTEvent(topic="v1/devices/me/rpc/response/1", payload={}),
        MQTTEvent(
            topic="v1/devices/me/rpc/response/1",
            payload={"No": "valid", "json": "format"},
        ),
        MQTTEvent(
            topic="v1/devices/me/rpc/response/1",
            payload={"response": {"without": "image"}},
        ),
        MQTTEvent(
            topic="v1/devices/me/rpc/response/1",
            payload={"response": {"Image": "NOTHEXADECIMAL"}},
        ),
    ],
)
def test_process_image_ignored_events(event: MQTTEvent) -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temporal:
        tmp = Path(temporal)
        state = CameraState(MagicMock(), MagicMock())
        state.image_dir_path.value = tmp
        state.mqtt_client = MagicMock()

        rpc = RPCWithResponse(state)
        rpc._process(event)
        assert not any(tmp.iterdir())


def test_process_image_on_no_path(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    state = CameraState(MagicMock(), MagicMock())
    state.mqtt_client = MagicMock()
    rpc = RPCWithResponse(state)

    valid_image_event = MQTTEvent(
        topic="v1/devices/me/rpc/response/1",
        payload={"response": {"Image", "RmFrZSBpbWFnZQ=="}},
    )

    rpc._process(valid_image_event)
    logs = caplog.records
    assert len(logs) > 0
    error_log: logging.LogRecord | None = None
    for log in logs:
        if log.message == "Invalid path to store images: None":
            error_log = log
    assert error_log
    assert error_log.levelname == "ERROR"


def test_process_image_on_invalid_type(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    state = CameraState(MagicMock(), MagicMock())
    state.mqtt_client = MagicMock()
    state.image_dir_path = TrackingVariable("/path/is/string")
    rpc = RPCWithResponse(state)

    valid_image_event = MQTTEvent(
        topic="v1/devices/me/rpc/response/1",
        payload={"response": {"Image", "RmFrZSBpbWFnZQ=="}},
    )

    rpc._process(valid_image_event)
    logs = caplog.records
    assert len(logs) > 0
    error_log: logging.LogRecord | None = None
    for log in logs:
        if log.message == "Invalid path to store images: /path/is/string":
            error_log = log
    assert error_log
    assert error_log.levelname == "ERROR"


def test_timestamp_format():
    ts = timestamp()
    assert len(ts) == len("20241108075403880")


def test_timestamp_value():
    fixed_datetime = datetime(2023, 1, 1, 12, 34, 56, 789000, tzinfo=timezone.utc)
    expected_timestamp = "20230101123456789"

    with patch(
        "local_console.clients.command.rpc_with_response.datetime"
    ) as mock_datetime:
        mock_datetime.now.return_value = fixed_datetime
        mock_datetime.strftime = datetime.strftime
        mock_datetime.now.timezone = timezone.utc

        assert timestamp() == expected_timestamp
