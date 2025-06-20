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
from local_console.commands.get import app
from local_console.commands.get import on_message_print_payload
from local_console.commands.get import on_message_telemetry
from local_console.core.camera.enums import MQTTTopics
from local_console.core.enums import GetObjects
from typer.testing import CliRunner

from tests.mocks.config import set_configuration
from tests.strategies.configs import generate_text
from tests.strategies.samplers.configs import GlobalConfigurationSampler


runner = CliRunner()


def test_get_deployment_command(single_device_config):
    with (
        patch("local_console.commands.get.Agent") as mock_agent,
        patch("local_console.commands.get.read_only_loop") as mock_read_loop,
    ):
        result = runner.invoke(app, [GetObjects.DEPLOYMENT.value])
        mock_read_loop.assert_called_once_with(
            mock_agent(),
            subs_topics=[MQTTTopics.ATTRIBUTES.value],
            message_task=on_message_print_payload,
        )
        assert result.exit_code == 0


def test_get_telemetry_command(single_device_config):
    with (
        patch("local_console.commands.get.Agent") as mock_agent,
        patch("local_console.commands.get.read_only_loop") as mock_read_loop,
    ):
        result = runner.invoke(app, [GetObjects.TELEMETRY.value])
        mock_read_loop.assert_called_once_with(
            mock_agent(),
            subs_topics=[MQTTTopics.TELEMETRY.value],
            message_task=on_message_telemetry,
        )
        assert result.exit_code == 0


@given(generate_text())
def test_get_instance_command(instance_id: str):
    set_configuration(GlobalConfigurationSampler(num_of_devices=1).sample())
    with (
        patch("local_console.commands.get.Agent") as mock_agent,
        patch("local_console.commands.get.read_only_loop") as mock_read_loop,
        patch("local_console.commands.get.on_message_instance") as mock_msg_inst,
    ):
        result = runner.invoke(app, [GetObjects.INSTANCE.value, instance_id])
        mock_read_loop.assert_called_once_with(
            mock_agent(),
            subs_topics=[MQTTTopics.ATTRIBUTES.value],
            message_task=mock_msg_inst.return_value,
        )
        assert result.exit_code == 0
        mock_msg_inst.assert_called_once_with(instance_id)
