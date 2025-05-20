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
from hypothesis import settings
from local_console.commands.qr import app
from typer.testing import CliRunner

from tests.mocks.config import set_configuration
from tests.strategies.configs import generate_valid_ip
from tests.strategies.samplers.configs import GlobalConfigurationSampler

runner = CliRunner()


@settings(deadline=300)
@given(st.booleans())
def test_qr_with_defaults(tls_enabled: bool) -> None:

    simple_gconf = GlobalConfigurationSampler(num_of_devices=1).sample()
    device_conf = simple_gconf.devices[0]
    set_configuration(simple_gconf)
    with (
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


@settings(deadline=None)
@given(
    generate_valid_ip(),
    st.booleans(),
    generate_valid_ip(),
)
def test_qr_with_overrides(
    host_override: str,
    tls_enable_override: bool,
    ntp_override: str,
) -> None:
    port_override = None
    simple_gconf = GlobalConfigurationSampler(num_of_devices=1).sample()
    device_conf = simple_gconf.devices[0]
    set_configuration(simple_gconf)
    with (
        patch("qrcode.main.QRCode"),
        patch("io.StringIO"),
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
            device_conf.mqtt.port,
            tls_enable_override,
            ntp_override,
            "",
            "",
            "",
            "",
            "",
            "",
        )


@settings(deadline=300)
@given(generate_valid_ip())
def test_qr_for_local_host(local_host_alias: str) -> None:
    """
    This test showcases how the command will generate the QR with the host set to the
    IP address that a camera could use over the local network, when the specified host
    is determined to match localhost.
    """
    simple_gconf = GlobalConfigurationSampler(num_of_devices=1).sample()
    device_conf = simple_gconf.devices[0]
    device_conf.mqtt.host = "1.2.3.4"
    set_configuration(simple_gconf)
    with (
        patch("local_console.commands.qr.is_localhost", return_value=True),
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
