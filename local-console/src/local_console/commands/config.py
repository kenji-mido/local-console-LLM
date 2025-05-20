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
from typing import Annotated
from typing import Any
from typing import Optional

import trio
import typer
from local_console.clients.agent import Agent
from local_console.commands.utils import find_device_config
from local_console.core.config import Config
from local_console.core.config import ConfigError
from local_console.core.helpers import device_configure
from local_console.core.helpers import initialize_handshake
from local_console.core.helpers import publish_configure
from local_console.core.schemas.schemas import DesiredDeviceConfig
from local_console.core.schemas.schemas import DeviceConnection
from local_console.core.schemas.schemas import GlobalConfiguration
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.plugin import PluginBase
from pydantic import ValidationError
from pydantic_core import to_jsonable_python

logger = logging.getLogger(__name__)
config_obj = Config()
app = typer.Typer(help="Configure devices, module instances, and Local Console")


@app.command(
    "get",
    help="Retrieve the value of a specific config key or display the entire configuration",
)
def config_get(
    ctx: typer.Context,
    section: Annotated[
        Optional[str],
        typer.Argument(
            help="Section of the configuration to retrieve. If not specified, the entire configuration is returned. "
            "Use dot notation to navigate through hierarchical sections, e.g., `mqtt.port`. "
        ),
    ] = None,
    device: Annotated[
        Optional[str],
        typer.Option(
            "--device",
            "-d",
            help="The name of the device to fetch the configuration parameter from. If not provided, the parameter will be fetched from the global configuration scope.",
        ),
    ] = None,
    port: Annotated[
        Optional[int],
        typer.Option(
            help="An alternative to --device, using the port to identify the device instead of its name. Ignored if the --device option is specified."
        ),
    ] = None,
) -> None:
    try:
        config: GlobalConfiguration | DeviceConnection = config_obj.data
        if device or port:
            config = find_device_config(device, port)

        selected_config = config

        if section:
            sections_split = section.split(".")
            for parameter in sections_split:
                selected_config = getattr(selected_config, parameter)

        print(json.dumps(selected_config, indent=2, default=to_jsonable_python))

    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        raise typer.Exit(1)


def _set(section: str, new: str | None, device: str | None, port: int | None) -> None:
    assert not section.startswith("evp.")

    device_config = find_device_config(device, port)

    selected_config = device_config
    sections_split = section.split(".")
    for parameter in sections_split[:-1]:
        selected_config = getattr(selected_config, parameter)

    parameter = sections_split[-1]
    if new is not None:
        new_val: Any = new if parameter != "port" else int(new)
    else:
        new_val = None

    try:
        setattr(selected_config, parameter, new_val)

        config_obj.save_config()
    except ValidationError as e:
        raise SystemExit(f"Error setting '{section}'. {e.errors()[0]['msg']}.")


@app.command("set", help="Sets the configuration key to the specified value")
def config_set(
    section: Annotated[
        str,
        typer.Argument(
            help="Section of the configuration to be modified. Use dot notation to express hierarchy, e.g., `mqtt.port`"
        ),
    ],
    new: Annotated[
        str,
        typer.Argument(
            help="New value to be used in the specified parameter of the section"
        ),
    ],
    device: Annotated[
        Optional[str],
        typer.Option(
            "--device",
            "-d",
            help="The name of the device to fetch the configuration parameter from. If not provided, the parameter will be set on the global configuration scope.",
        ),
    ] = None,
    port: Annotated[
        Optional[int],
        typer.Option(
            help="An alternative to --device, using the port to identify the device instead of its name. Ignored if the --device option is specified."
        ),
    ] = None,
) -> None:
    _set(section, new, device, port)


@app.command("unset", help="Removes the value of a nullable configuration key")
def config_unset(
    section: Annotated[
        str,
        typer.Argument(
            help="Section of the configuration to be unset. Use dot notation to express hierarchy, e.g., `mqtt.port`"
        ),
    ],
    device: Annotated[
        Optional[str],
        typer.Option(
            "--device",
            "-d",
            help="The name of the device to fetch the configuration parameter from. If not provided, the parameter will be unset on the global configuration scope.",
        ),
    ] = None,
    port: Annotated[
        Optional[int],
        typer.Option(
            help="An alternative to --device, using the port to identify the device instead of its name. Ignored if the --device option is specified."
        ),
    ] = None,
) -> None:
    _set(section, None, device, port)


@app.command("instance", help="Configure an application module instance")
def config_instance(
    instance_id: Annotated[
        str,
        typer.Argument(help="Target instance of the configuration"),
    ],
    topic: Annotated[
        str,
        typer.Argument(help="Topic of the configuration"),
    ],
    config: Annotated[
        str,
        typer.Argument(help="Data of the configuration"),
    ],
    port: Annotated[
        Optional[int],
        typer.Option(help="TCP port on which the MQTT broker is listening"),
    ] = None,
) -> None:
    try:
        trio.run(configure_task, instance_id, topic, config, port)
    except ConnectionError:
        raise SystemExit(
            f"Connection error while attempting to set configuration topic '{topic}' for instance {instance_id}"
        )


async def configure_task(
    instance_id: str, topic: str, cfg: str, port: int | None = None
) -> None:
    if not port:
        config_device = config_obj.get_first_device_config()
    else:
        config_device = find_device_config(None, port)
    schema = config_device.onwire_schema
    agent = Agent(config_device.mqtt.port)
    await initialize_handshake(agent)
    async with agent.mqtt_scope([]):
        await publish_configure(agent, schema, instance_id, topic, cfg)


@app.command("device", help="Configure the device")
def config_device(
    interval_max: Annotated[
        int,
        typer.Argument(help="Max interval to report"),
    ],
    interval_min: Annotated[
        int,
        typer.Argument(help="Min interval to report"),
    ],
    device: Annotated[
        Optional[str],
        typer.Option(
            "--device",
            "-d",
            help="The name of the device to update the configuration. If omitted it will update the first device on the list.",
        ),
    ] = None,
    port: Annotated[
        Optional[int],
        typer.Option(
            help="An alternative to --device, using the port to identify the device instead of its name. Ignored if the --device option is specified."
        ),
    ] = None,
) -> None:
    retcode = 1
    try:
        device_config = find_device_config(device, port)
        desired_device_config = DesiredDeviceConfig(
            reportStatusIntervalMax=interval_max, reportStatusIntervalMin=interval_min
        )
        retcode = trio.run(config_device_task, desired_device_config, device_config)
    except ValueError:
        logger.warning("Report status interval out of range.")
    except ConnectionError:
        raise SystemExit(
            "Connection error while attempting to set device configuration"
        )
    raise typer.Exit(code=retcode)


async def config_device_task(
    desired_device_config: DesiredDeviceConfig, config_device: DeviceConnection
) -> int:
    retcode = 1
    schema = config_device.onwire_schema
    agent = Agent(config_device.mqtt.port)
    if schema == OnWireProtocol.EVP2:
        async with agent.mqtt_scope([]):
            await device_configure(agent, schema, desired_device_config)
        retcode = 0
    else:
        logger.warning(f"Unsupported on-wire schema {schema} for this command.")
    return retcode


class ConfigCommand(PluginBase):
    implementer = app
