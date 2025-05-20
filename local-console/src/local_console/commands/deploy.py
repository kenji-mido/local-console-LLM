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
from pathlib import Path
from typing import Annotated
from typing import Optional
from unittest.mock import patch

import trio
import typer
from local_console.commands.utils import dummy_report_fn
from local_console.commands.utils import find_device_config
from local_console.core.camera.machine import Camera
from local_console.core.camera.states.v2.ready import ReadyCameraV2
from local_console.core.commands.deploy import DeploymentSpec
from local_console.core.commands.deploy import DeployStage
from local_console.core.config import Config
from local_console.core.enums import config_paths
from local_console.core.enums import ModuleExtension
from local_console.core.enums import Target
from local_console.core.schemas.schemas import DeploymentManifest
from local_console.core.schemas.schemas import DeviceConnection
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.plugin import PluginBase
from local_console.servers.webserver import AsyncWebserver
from local_console.servers.webserver import FileInbox

logger = logging.getLogger(__name__)

app = typer.Typer()


@app.command(help="Command for deploying application to the agent")
def deploy(
    empty: Annotated[
        bool,
        typer.Option(
            "-e",
            "--empty",
            help="Option to remove previous deployment with an empty one",
        ),
    ] = False,
    signed: Annotated[
        bool,
        typer.Option(
            "-s",
            "--signed",
            help="Option to deploy signed files (already built with the 'build' command)",
        ),
    ] = False,
    timeout: Annotated[
        int,
        typer.Option(
            "-t",
            "--timeout",
            help="Set timeout to wait for the modules to be downloaded by the agent",
        ),
    ] = 15,
    target: Annotated[
        Optional[Target],
        typer.Argument(
            help="Optional argument to specify which AoT compilation to deploy. If not defined it will deploy the plain WASM"
        ),
    ] = None,
    device: Annotated[
        Optional[str],
        typer.Option(
            "--device",
            "-d",
            help="The name of the device to which the application will be deployed.",
        ),
    ] = None,
    port: Annotated[
        Optional[int],
        typer.Option(
            help="An alternative to --device, using the port to identify the device instead of its name. Ignored if the --device option is specified."
        ),
    ] = None,
) -> None:
    config_device = find_device_config(device, port)

    if empty:
        spec = DeploymentSpec.new_empty()
    else:
        bin_fp = Path.cwd() / config_paths.bin
        if not bin_fp.is_dir():
            raise Exception(f"'bin' folder does not exist at {bin_fp.parent}")

        spec = user_provided_manifest_setup(
            bin_fp,
            target,
            signed,
        )

    try:
        trio.run(deploy_task, spec, config_device, timeout)
    except Exception as e:
        logger.exception("Deployment error", exc_info=e)
        raise typer.Exit(code=1)


class DeployCommand(PluginBase):
    implementer = app


def user_provided_manifest_setup(
    files_dir: Path,
    target_arch: Optional[Target],
    use_signed: bool,
) -> DeploymentSpec:
    """
    Fill all fields in of a preliminary deployment manifest that
    comes with a set of modules specified, having their file paths
    set in the corresponding module's `downloadUrl` field.

    All module files must be located in `files_dir`
    """
    from_user = Config().get_deployment()
    pre = DeploymentSpec(modules={}, pre_deployment=from_user.deployment)
    for ident in pre.pre_deployment.modules.keys():
        pre.modules[ident] = project_binary_lookup(
            files_dir, ident, target_arch, use_signed
        )

    return pre


async def deploy_task(
    spec: DeploymentSpec,
    config: DeviceConnection,
    timeout_secs: int = 30,
) -> None:
    """
    This command assumes the device to be in its 'ready' state
    """
    from local_console.core.camera.states.v1.ready import ReadyCameraV1
    from local_console.core.camera.states.v2.ready import ReadyCameraV2

    schema = config.onwire_schema

    # No need to spawn a broker
    with patch("local_console.core.camera.states.base.spawn_broker"):
        try:
            async with (
                trio.open_nursery() as nursery,
                AsyncWebserver() as webserver,
            ):

                send, _ = trio.open_memory_channel(0)
                token = trio.lowlevel.current_trio_token()
                camera = Camera(
                    config,
                    send,
                    webserver,
                    FileInbox(webserver),
                    token,
                    dummy_report_fn,
                )

                state = (
                    ReadyCameraV1(camera._common_properties)
                    if schema == OnWireProtocol.EVP1
                    else ReadyCameraV2(camera._common_properties)
                )

                await nursery.start(camera.setup)
                await camera._transition_to_state(state)

                event = trio.Event()

                assert hasattr(
                    state, "start_app_deployment"
                )  # due to the different returned type, mypy doesn't acknowledge the shared method
                await state.start_app_deployment(
                    spec, event, print, stage_callback, timeout_secs
                )

                await event.wait()
                nursery.cancel_scope.cancel()

        except* KeyboardInterrupt:
            logger.info("Cancelled by the user")


def project_binary_lookup(
    files_dir: Path,
    module_base_name: str,
    target_arch: Optional[Target],
    use_signed: bool,
) -> Path:
    """
    Looks for a built WASM module file that is named by following the
    file naming convention selected at the command line by the flags.
    """
    assert files_dir.is_dir()

    name_parts: list[str] = [module_base_name]

    if use_signed and target_arch:
        name_parts.append(ModuleExtension.SIGNED.value)

    if target_arch:
        name_parts += [target_arch.value, ModuleExtension.AOT.value]
    else:
        name_parts.append(ModuleExtension.WASM.value)

    binary = files_dir / ".".join(name_parts)
    if not binary.is_file():
        raise FileNotFoundError(f"{binary} not found.")

    if use_signed and not target_arch:
        logger.warning(
            f"There is no target architecture, the {binary} module to be deployed is not signed"
        )

    return binary


async def stage_callback(
    stage: DeployStage, manifest: DeploymentManifest | None
) -> None:
    if stage == DeployStage.Done:
        assert manifest
        logger.info("Successfully applied manifest.")

        path = Path(config_paths.deployment_json)
        path.write_text(json.dumps(manifest.model_dump(), indent=2))
        logger.info(f"Saved deployment manifest to: {path}")
