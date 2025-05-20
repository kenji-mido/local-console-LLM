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
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import ANY
from unittest.mock import patch

import hypothesis.strategies as st
import pytest
import trio
from hypothesis import given
from local_console.commands.deploy import app
from local_console.commands.deploy import deploy_task
from local_console.commands.deploy import project_binary_lookup
from local_console.commands.deploy import stage_callback
from local_console.commands.deploy import user_provided_manifest_setup
from local_console.core.commands.deploy import DeploymentSpec
from local_console.core.enums import Target
from local_console.core.schemas.schemas import DeploymentManifest
from local_console.core.schemas.schemas import OnWireProtocol
from typer.testing import CliRunner

from tests.mocks.config import set_configuration
from tests.strategies.samplers.configs import GlobalConfigurationSampler
from tests.strategies.samplers.deploy import DeploymentSampler

runner = CliRunner()


@contextmanager
def user_setup_for_deploy() -> None:

    sample_deploy = DeploymentSampler().sample(1)
    sample_manifest = DeploymentManifest(deployment=sample_deploy)
    with (
        patch("pathlib.Path.is_dir", return_value=True),
        patch(
            "local_console.core.config.Config.get_deployment",
            return_value=sample_manifest,
        ),
    ):
        yield


def test_deploy_empty_command() -> None:
    with (
        patch("trio.run") as mock_exec,
        patch(
            "local_console.commands.deploy.DeploymentSpec.new_empty"
        ) as mock_get_empty_spec,
        patch(
            "local_console.commands.deploy.project_binary_lookup"
        ) as mock_look_module_up,
    ):
        result = runner.invoke(app, ["-e"])
        assert result.exit_code == 0

        mock_get_empty_spec.assert_called_once()
        mock_look_module_up.assert_not_called()
        mock_exec.assert_called_once()


@given(st.sampled_from(Target))
def test_deploy_command_target(
    target: Target,
) -> None:

    simple_gconf = GlobalConfigurationSampler(num_of_devices=1).sample()
    set_configuration(simple_gconf)
    with (
        user_setup_for_deploy(),
        patch("trio.run") as mock_exec,
        patch(
            "local_console.commands.deploy.DeploymentSpec.new_empty"
        ) as mock_get_empty_spec,
        patch(
            "local_console.commands.deploy.project_binary_lookup"
        ) as mock_look_module_up,
        patch("pathlib.Path.is_dir"),
    ):
        result = runner.invoke(app, [target.value])
        assert result.exit_code == 0

        mock_get_empty_spec.assert_not_called()
        mock_look_module_up.assert_called_once_with(ANY, ANY, target, ANY)
        mock_exec.assert_called_once()


def test_deploy_command_signed(single_device_config) -> None:
    with (
        user_setup_for_deploy(),
        patch("trio.run") as mock_exec,
        patch(
            "local_console.commands.deploy.DeploymentSpec.new_empty"
        ) as mock_get_empty_spec,
        patch(
            "local_console.commands.deploy.project_binary_lookup"
        ) as mock_look_module_up,
        patch("pathlib.Path.is_dir"),
    ):
        result = runner.invoke(app, ["-s"])
        assert result.exit_code == 0

        mock_get_empty_spec.assert_not_called()
        mock_look_module_up.assert_called_once_with(ANY, ANY, ANY, True)
        mock_exec.assert_called_once()


def test_deploy_command_timeout(single_device_config) -> None:
    timeout = 6
    dev_conf = single_device_config.devices[0]

    with (
        user_setup_for_deploy(),
        patch("trio.run") as mock_exec,
        patch(
            "local_console.commands.deploy.DeploymentSpec.new_empty"
        ) as mock_get_empty_spec,
        patch(
            "local_console.commands.deploy.project_binary_lookup"
        ) as mock_look_module_up,
        patch("pathlib.Path.is_dir"),
    ):
        runner.invoke(app, ["-t", timeout])

        mock_get_empty_spec.assert_not_called()
        mock_look_module_up.assert_called_once()
        mock_exec.assert_called_once_with(deploy_task, ANY, dev_conf, timeout)


@given(
    st.booleans(),
    st.integers(),
    st.sampled_from(Target),
)
def test_deploy_manifest_no_bin(
    signed: bool,
    timeout: int,
    target: Target,
):
    set_configuration(GlobalConfigurationSampler(num_of_devices=1).sample())
    with (
        user_setup_for_deploy(),
        patch("trio.run") as mock_exec,
        patch(
            "local_console.commands.deploy.DeploymentSpec.new_empty"
        ) as mock_get_empty_spec,
        patch(
            "local_console.commands.deploy.Path.is_dir", return_value=False
        ) as mock_is_dir,
        patch(
            "local_console.commands.deploy.project_binary_lookup"
        ) as mock_look_module_up,
    ):
        result = runner.invoke(
            app, ["-t", timeout, *(["-s"] if signed else []), target.value]
        )
        assert result.exit_code != 0

        mock_get_empty_spec.assert_not_called()
        mock_is_dir.assert_called_once()
        mock_look_module_up.assert_not_called()
        mock_exec.assert_not_called()


def test_project_binary_lookup_no_interpreted_wasm(tmp_path):
    with pytest.raises(FileNotFoundError):
        project_binary_lookup(tmp_path, "node", None, False)


@given(st.booleans())
def test_project_binary_lookup_no_arch(signed):

    parent = Path("some_dir")
    mod_file = parent / "node.wasm"
    with (
        patch("pathlib.Path.is_dir", return_value=True),
        patch("pathlib.Path.is_file", return_value=True),
    ):
        assert project_binary_lookup(parent, "node", None, signed) == mod_file


def test_multiple_module_setup(tmp_path):

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    classification_file = bin_dir / "classification.signed.xtensa.aot"
    classification_file.touch()
    detection_file = bin_dir / "detection.signed.xtensa.aot"
    detection_file.touch()
    manifest = DeploymentManifest.model_validate(
        {
            "deployment": {
                "deploymentId": "0000aaaa",
                "instanceSpecs": {
                    "classi": {
                        "moduleId": "classification",
                        "subscribe": {},
                        "publish": {},
                    },
                    "detect": {
                        "moduleId": "classification",
                        "subscribe": {},
                        "publish": {},
                    },
                },
                "modules": {
                    "classification": {
                        "entryPoint": "main",
                        "moduleImpl": "wasm",
                        "downloadUrl": "",
                        "hash": "00",
                    },
                    "detection": {
                        "entryPoint": "main",
                        "moduleImpl": "wasm",
                        "downloadUrl": "",
                        "hash": "00",
                    },
                },
                "publishTopics": {},
                "subscribeTopics": {},
            }
        }
    )

    with (
        patch("local_console.core.config.Config.get_deployment", return_value=manifest),
    ):
        dm = user_provided_manifest_setup(
            bin_dir,
            Target.XTENSA,
            True,
        )

        assert "classi" in dm.pre_deployment.instanceSpecs
        assert "detect" in dm.pre_deployment.instanceSpecs
        assert all(Target.XTENSA.value in str(mod) for mod in dm.modules.values())


@pytest.mark.parametrize(
    "signed, file_name",
    [
        (False, "node.xtensa.aot"),
        (True, "node.signed.xtensa.aot"),
    ],
)
def test_project_binary_lookup_with_arch(signed, file_name, tmp_path):

    base_file = tmp_path / "node.wasm"
    base_file.touch()

    mod_file = tmp_path / file_name
    mod_file.touch()

    assert project_binary_lookup(tmp_path, "node", Target.XTENSA, signed) == mod_file


@pytest.mark.trio
@pytest.mark.parametrize(
    "schema",
    [
        OnWireProtocol.EVP1,
        OnWireProtocol.EVP2,
    ],
)
async def test_deploy_task(schema, nursery, single_device_config) -> None:

    some_spec = DeploymentSpec.new_empty()

    device_conf = single_device_config.devices[0]
    device_conf.onwire_schema = schema

    some_timeout = 15

    async def _mock_mqtt_setup(self, *, task_status: Any = trio.TASK_STATUS_IGNORED):
        task_status.started(True)

    async def mock_start_app_deployment(
        self, target_spec, event_flag, error_notify, stage_notify_fn, timeout_secs
    ):
        assert target_spec == some_spec
        assert error_notify == print
        assert stage_callback == stage_notify_fn
        assert timeout_secs == some_timeout
        event_flag.set()

    with (
        patch("local_console.core.camera.states.base.MQTTDriver"),
        patch("local_console.core.camera.states.common.TimeoutBehavior"),
        patch("local_console.core.camera.states.v2.ready.TimeoutBehavior"),
        patch("local_console.commands.utils.AsyncWebserver"),
        patch(
            "local_console.core.camera.states.v1.ready.ReadyCameraV1.start_app_deployment",
            mock_start_app_deployment,
        ),
        patch(
            "local_console.core.camera.states.v2.ready.ReadyCameraV2.start_app_deployment",
            mock_start_app_deployment,
        ),
    ):
        await deploy_task(some_spec, device_conf, some_timeout)
