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

import hypothesis.strategies as st
from hypothesis import given
from local_console.commands.qr import app
from typer.testing import CliRunner

from tests.mocks.mock_configs import config_without_io
from tests.strategies.configs import generate_valid_ip
from tests.strategies.configs import generate_valid_port_number
from tests.strategies.samplers.configs import GlobalConfigurationSampler

runner = CliRunner()


@given(st.booleans())
def test_qr_with_defaults(tls_enabled: bool) -> None:

    simple_gconf = GlobalConfigurationSampler(num_of_devices=1).sample()
    device_conf = simple_gconf.devices[0]
    device_conf.webserver.host = "http_server"
    with (
        config_without_io(simple_gconf),
        patch(
            "local_console.commands.qr.config_obj.get_active_device_config",
            return_value=device_conf,
        ) as mock_device_config,
        patch("local_console.commands.qr.is_localhost", return_value=False),
        patch("local_console.commands.qr.get_mqtt_ip", return_value="1.2.3.4"),
        patch(
            "local_console.core.camera.qr.qr.qr_string", return_value=""
        ) as mock_qr_string,
    ):
        args = []
        if tls_enabled:
            args.append("--tls")
        result = runner.invoke(app, args)
        assert result.exit_code == 0

        mock_qr_string.assert_called_once_with(
            device_conf.mqtt.host,
            device_conf.mqtt.port,
            tls_enabled,
            "pool.ntp.org",
            "",
            "",
            "",
            "",
            "",
            "",
        )
        mock_device_config.assert_called()


@given(
    generate_valid_ip(),
    generate_valid_port_number(),
    st.booleans(),
    generate_valid_ip(),
)
def test_qr_with_overrides(
    host_override: str,
    port_override: int,
    tls_enable_override: bool,
    ntp_override: str,
) -> None:
    simple_gconf = GlobalConfigurationSampler(num_of_devices=1).sample()
    device_conf = simple_gconf.devices[0]
    device_conf.webserver.host = "http_server"
    with (
        config_without_io(simple_gconf),
        patch(
            "local_console.commands.qr.config_obj.get_active_device_config",
            return_value=device_conf,
        ) as mock_device_config,
        patch("local_console.commands.qr.is_localhost", return_value=False),
        patch("local_console.commands.qr.get_mqtt_ip", return_value="1.2.3.4"),
        patch(
            "local_console.core.camera.qr.qr.qr_string", return_value=""
        ) as mock_qr_string,
    ):
        args = [
            "--host",
            host_override,
            "--port",
            port_override,
            *(("--tls",) if tls_enable_override else ()),
            "--ntp-server",
            ntp_override,
        ]
        result = runner.invoke(app, args)
        assert result.exit_code == 0

        mock_qr_string.assert_called_once_with(
            host_override,
            port_override,
            tls_enable_override,
            ntp_override,
            "",
            "",
            "",
            "",
            "",
            "",
        )
        mock_device_config.assert_called()


@given(generate_valid_ip())
def test_qr_for_local_host(local_host_alias: str) -> None:
    """
    This test showcases how the command will generate the QR with the host set to the
    IP address that a camera could use over the local network, when the specified host
    is determined to match localhost.
    """
    simple_gconf = GlobalConfigurationSampler(num_of_devices=1).sample()
    device_conf = simple_gconf.devices[0]
    device_conf.webserver.host = "http_server"
    with (
        config_without_io(simple_gconf),
        patch(
            "local_console.commands.qr.config_obj.get_active_device_config",
            return_value=device_conf,
        ) as mock_device_config,
        patch("local_console.commands.qr.is_localhost", return_value=True),
        patch("local_console.commands.qr.get_mqtt_ip", return_value="1.2.3.4"),
        patch(
            "local_console.core.camera.qr.qr.qr_string", return_value=""
        ) as mock_qr_string,
    ):
        result = runner.invoke(app, ["--host", local_host_alias])
        assert result.exit_code == 0

        mock_qr_string.assert_called_once_with(
            "1.2.3.4",
            device_conf.mqtt.port,
            False,
            "pool.ntp.org",
            "",
            "",
            "",
            "",
            "",
            "",
        )
        mock_device_config.assert_called()
