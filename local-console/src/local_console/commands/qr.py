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
import io
import logging
from pathlib import Path
from typing import Annotated
from typing import Optional

import typer
from local_console.commands.utils import find_device_config
from local_console.core.camera.qr.qr import get_qr_object
from local_console.plugin import PluginBase
from local_console.utils.local_network import is_localhost

logger = logging.getLogger(__name__)

app = typer.Typer()


@app.command(
    help=(
        "Command to generate a QR code for camera onboarding. "
        "Host and port options default to the configured values in the CLI"
    )
)
def qr(
    host: Annotated[
        Optional[str],
        typer.Option(help="Host address for the MQTT broker"),
    ] = None,
    device: Annotated[
        Optional[str],
        typer.Option(
            "--device",
            "-d",
            help="The name of the device used to identify the configuration with MQTT host information. If the host is set to localhost, it will be replaced with your system's IP address.",
        ),
    ] = None,
    port: Annotated[
        Optional[int],
        typer.Option(
            help="An alternative to --device, using the port to identify the device instead of its name. Ignored if the --device option is specified."
        ),
    ] = None,
    enable_tls: Annotated[
        bool,
        typer.Option("--tls", "-t", help="Whether to connect using TLS"),
    ] = False,
    ntp_server: Annotated[
        str,
        typer.Option(help="NTP server to connect to for time synchronization"),
    ] = "pool.ntp.org",
    save_png: Annotated[
        Optional[Path],
        typer.Option(help="PNG file name to which save QR code to"),
    ] = None,
) -> None:
    # Take default values from the configured settings
    device_config = find_device_config(device, port)
    host = device_config.mqtt.host if not host else host
    port = device_config.mqtt.port
    tls_enabled = enable_tls

    local_ip = device_config.mqtt.host
    if is_localhost(host) or host == local_ip:
        host = local_ip

    qr_code = get_qr_object(host, port, tls_enabled, ntp_server)
    if save_png:
        img = qr_code.make_image(fill_color="black", back_color="white")
        img.save(save_png.expanduser())

    # Print the code in the terminal
    f = io.StringIO()
    qr_code.print_ascii(out=f)
    f.seek(0)
    print(f.read())


class QRCommand(PluginBase):
    implementer = app
