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
from unittest.mock import patch

from hypothesis import given
from local_console.commands.rpc import app
from local_console.core.config import Config
from local_console.core.schemas.schemas import OnWireProtocol
from typer.testing import CliRunner

from tests.mocks.config import set_configuration
from tests.strategies.configs import generate_text

runner = CliRunner()


@given(
    generate_text(),
    generate_text(),
    generate_text(),
)
def test_v1_rpc_command(instance_id: str, method: str, params: str):
    set_configuration()
    Config().get_first_device_config().onwire_schema = OnWireProtocol.EVP1
    with (
        patch(
            "local_console.core.camera.states.v1.common.run_rpc_with_response"
        ) as mock_v1_run_rpc_with_response,
    ):
        # Format params to be a valid JSON
        params = {"key": params}
        result = runner.invoke(app, [instance_id, method, json.dumps(params)])
        mock_v1_run_rpc_with_response.assert_called_with(
            Config().get_first_device_config().id, instance_id, method, params
        )
        assert result.exit_code == 0


@given(
    generate_text(),
    generate_text(),
    generate_text(),
)
def test_v1_rpc_command_exception(instance_id: str, method: str, params: str):
    set_configuration()
    Config().get_first_device_config().onwire_schema = OnWireProtocol.EVP1
    with (patch("local_console.core.camera.states.v1.common.run_rpc_with_response"),):
        # Format params not to be a valid JSON
        params = params + "}"
        result = runner.invoke(app, [instance_id, method, params])
        assert result.exit_code == 1
