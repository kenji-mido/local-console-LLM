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
from unittest.mock import patch

from hypothesis import given
from hypothesis import strategies as st
from local_console.commands.logs import app
from local_console.commands.logs import request_instance_logs
from local_console.commands.utils import find_device_config
from local_console.core.camera.enums import MQTTTopics
from typer.testing import CliRunner

from tests.mocks.config import set_configuration
from tests.strategies.configs import generate_text

runner = CliRunner()


@given(
    generate_text(),
    st.integers(),
)
def test_logs_command(
    instance_id: str,
    timeout: int,
):
    set_configuration()
    with (
        patch("local_console.commands.logs.Agent") as mock_agent_client,
        patch("local_console.commands.logs.read_only_loop") as mock_read_loop,
        patch("trio.run") as mock_run,
        patch("local_console.commands.logs.on_message_logs") as mock_msg_logs,
    ):
        result = runner.invoke(app, ["--timeout", timeout, instance_id])
        mock_run.assert_called_with(
            request_instance_logs, instance_id, find_device_config(None, None)
        )
        mock_read_loop.assert_called_once_with(
            mock_agent_client(),
            subs_topics=[MQTTTopics.TELEMETRY.value],
            message_task=mock_msg_logs.return_value,
        )
        assert result.exit_code == 0
        mock_msg_logs.assert_called_once_with(instance_id, timeout)


@given(
    generate_text(),
    st.integers(),
)
def test_logs_command_exception(instance_id: str, timeout: int):
    set_configuration()
    with (
        patch("local_console.commands.logs.Agent") as mock_agent_client,
        patch("local_console.commands.logs.read_only_loop") as mock_read_loop,
        patch("trio.run") as mock_run,
    ):
        mock_read_loop.side_effect = ConnectionError
        result = runner.invoke(app, ["--timeout", timeout, instance_id])
        mock_agent_client.assert_called()
        mock_run.assert_called()
        assert result.exit_code == 1
