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
import hashlib
import json
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import ANY
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
import trio
from local_console.core.camera.enums import DeployStage
from local_console.core.camera.enums import MQTTSubTopics
from local_console.core.camera.enums import MQTTTopics
from local_console.core.camera.states.v2.deployment import ConfigureAppToRunning
from local_console.core.camera.v2.components.edge_app import EdgeAppCommonSettings
from local_console.core.camera.v2.components.edge_app import EdgeAppPortSettings
from local_console.core.camera.v2.components.edge_app import EdgeAppSpec
from local_console.core.camera.v2.components.edge_app import ProcessState
from local_console.core.camera.v2.components.edge_app import UploadSpec
from local_console.core.camera.v2.components.req_res_info import ReqInfo
from local_console.core.camera.v2.components.req_res_info import ResponseCode
from local_console.core.commands.deploy import DeploymentSpec
from local_console.core.commands.deploy import single_module_manifest_setup
from local_console.core.enums import ModuleExtension
from local_console.core.schemas.schemas import Deployment
from local_console.core.schemas.schemas import DeploymentManifest
from local_console.core.schemas.schemas import Module
from local_console.core.schemas.schemas import OnWireProtocol

from tests.mocks.method_extend import MethodObserver
from tests.strategies.samplers.configs import GlobalConfigurationSampler
from tests.strategies.samplers.deploy import DeploymentSampler
from tests.strategies.samplers.mqtt_message import MockMQTTMessage


@pytest.fixture(
    params=[
        ModuleExtension.PY.as_suffix,
        ModuleExtension.WASM.as_suffix,
        ModuleExtension.AOT.as_suffix,
        ModuleExtension.SIGNED.as_suffix,
    ]
)
def file_extension(request):
    return request.param


def test_get_spec_for_empty_deployment():
    spec_empty = DeploymentSpec.new_empty()
    assert len(spec_empty.modules) == 0
    assert len(spec_empty.pre_deployment.modules) == 0
    assert len(spec_empty.pre_deployment.instanceSpecs) == 0
    assert len(spec_empty.pre_deployment.deploymentId) != 0


@pytest.mark.trio
async def test_callback_on_stage_transitions_v1(
    camera,
    mocked_agent_fixture,
    nursery,
    monkeypatch,
) -> None:
    mqtt_client = mocked_agent_fixture
    obs = MethodObserver(monkeypatch)
    event_flag = trio.Event()
    error_cb = Mock()
    stage_cb = AsyncMock()

    # We're mocking out the deployment manifest
    # rendering logic, as it is tested at ::test_deployment_setup.
    deploy_sample = DeploymentSampler().sample(1)
    target_manifest = DeploymentManifest(deployment=deploy_sample)
    monkeypatch.setattr(
        DeploymentSpec, "render_for_webserver", lambda _a, _b, _c: target_manifest
    )
    spec = DeploymentSpec(modules={}, pre_deployment=deploy_sample)

    with (
        patch("local_console.core.camera.states.base.spawn_broker"),
        patch("local_console.core.commands.deploy.SyncWebserver"),
        patch("local_console.core.camera.states.v1.deployment.TimeoutBehavior"),
        patch(
            "local_console.core.camera.states.v1.deployment.publish_deploy"
        ) as mock_push_deploy,
    ):
        from local_console.core.camera.states.v1.ready import ReadyCameraV1
        from local_console.core.camera.states.v1.deployment import ClearingAppCameraV1
        from local_console.core.camera.states.v1.deployment import DeployingAppCameraV1

        # This setup helps awaiting for message processing
        obs.hook(ClearingAppCameraV1, "on_message_received")
        obs.hook(DeployingAppCameraV1, "on_message_received")

        # Set starting state up
        state_props = camera._common_properties
        await nursery.start(camera.setup)
        start_state = ReadyCameraV1(state_props)
        await camera._transition_to_state(start_state)

        await camera.start_app_deployment(spec, event_flag, error_cb, stage_cb, ANY)

        ### Assert first phase: clear a previous deployment away
        assert camera.current_state is ClearingAppCameraV1
        first_stage = DeployStage.WaitAppliedConfirmation
        stage_cb.assert_awaited_once_with(first_stage, ANY)
        stage_cb.reset_mock()
        mock_push_deploy.assert_awaited_with(
            mqtt_client.agent, OnWireProtocol.EVP1, ANY
        )
        mock_push_deploy.reset_mock()

        # The generated deploy ID for this phase is different than that of the target deployment
        assert (
            camera._state._to_deploy.deployment.deploymentId
            != target_manifest.deployment.deploymentId
        )

        # Simulate success message
        mqtt_client.receives(
            MockMQTTMessage(
                topic=MQTTTopics.ATTRIBUTES.value,
                payload=json.dumps(
                    {
                        MQTTSubTopics.DEPLOY_STATUS.value: json.dumps(
                            {
                                "deploymentId": camera._state._to_deploy.deployment.deploymentId,
                                "reconcileStatus": "ok",
                            }
                        )
                    }
                ),
            )
        )

        ### Assert second phase: push the deployment
        await obs.wait_for()
        assert camera.current_state is DeployingAppCameraV1
        stage_cb.assert_awaited_once_with(DeployStage.WaitAppliedConfirmation, ANY)
        stage_cb.reset_mock()
        mock_push_deploy.assert_awaited_with(
            mqtt_client.agent, OnWireProtocol.EVP1, target_manifest
        )
        mock_push_deploy.reset_mock()
        # The generated deploy ID for this phase is **equal to*** that of the target deployment
        assert (
            camera._state._to_deploy.deployment.deploymentId
            == target_manifest.deployment.deploymentId
        )

        # final step: success, then go back to the 'ready' state
        mqtt_client.receives(
            MockMQTTMessage(
                topic=MQTTTopics.ATTRIBUTES.value,
                payload=json.dumps(
                    {
                        MQTTSubTopics.DEPLOY_STATUS.value: json.dumps(
                            {
                                "deploymentId": camera._state._to_deploy.deployment.deploymentId,
                                "reconcileStatus": "ok",
                            }
                        )
                    }
                ),
            )
        )
        await obs.wait_for()
        assert event_flag.is_set()
        error_cb.assert_not_called()
        stage_cb.assert_awaited_once_with(DeployStage.Done, ANY)
        assert camera.current_state is ReadyCameraV1

        mqtt_client.stop_receiving_messages()
        nursery.cancel_scope.cancel()


@pytest.mark.trio
async def test_callback_on_stage_transitions_v2(
    camera,
    mocked_agent_fixture,
    nursery,
    monkeypatch,
) -> None:
    mqtt_client = mocked_agent_fixture
    obs = MethodObserver(monkeypatch)
    event_flag = trio.Event()
    error_cb = Mock()
    stage_cb = AsyncMock()

    # We're mocking out the deployment manifest
    # rendering logic, as it is tested at ::test_deployment_setup.
    deploy_sample = DeploymentSampler().sample(1)
    target_manifest = DeploymentManifest(deployment=deploy_sample)
    monkeypatch.setattr(
        DeploymentSpec, "render_for_webserver", lambda _a, _b, _c: target_manifest
    )
    spec = DeploymentSpec(modules={}, pre_deployment=deploy_sample)

    req_id = "12345"
    from local_console.core.camera.states.v2.deployment import ConnectedCameraStateV2

    with (
        patch("local_console.core.camera.states.base.spawn_broker"),
        patch("local_console.core.commands.deploy.SyncWebserver"),
        patch("local_console.core.camera.states.v2.deployment.TimeoutBehavior"),
        patch(
            "local_console.core.camera.states.v2.deployment.publish_deploy"
        ) as mock_push_deploy,
        patch(
            "local_console.core.camera.states.v2.deployment.random_id",
            return_value=req_id,
        ),
        patch.object(
            ConnectedCameraStateV2, "send_configuration"
        ) as mock_send_configuration,
    ):
        from local_console.core.camera.states.v2.ready import ReadyCameraV2
        from local_console.core.camera.states.v2.deployment import ClearingAppCameraV2
        from local_console.core.camera.states.v2.deployment import DeployingAppCameraV2
        from local_console.core.camera.states.v2.deployment import ConfigureAppToRunning

        # This setup helps awaiting for message processing
        obs.hook(ClearingAppCameraV2, "on_message_received")
        obs.hook(DeployingAppCameraV2, "on_message_received")
        obs.hook(ConfigureAppToRunning, "on_message_received")

        # Set starting state up
        state_props = camera._common_properties
        await nursery.start(camera.setup)
        start_state = ReadyCameraV2(state_props)
        await camera._transition_to_state(start_state)

        await camera.start_app_deployment(spec, event_flag, error_cb, stage_cb, ANY)

        ### Assert first phase: clear a previous deployment away
        assert camera.current_state is ClearingAppCameraV2
        first_stage = DeployStage.WaitAppliedConfirmation
        stage_cb.assert_awaited_once_with(first_stage, ANY)
        stage_cb.reset_mock()
        mock_push_deploy.assert_awaited_once_with(
            mqtt_client.agent, OnWireProtocol.EVP2, ANY
        )
        mock_push_deploy.reset_mock()

        # The generated deploy ID for this phase is different than that of the target deployment
        assert (
            camera._state._to_deploy.deployment.deploymentId
            != target_manifest.deployment.deploymentId
        )

        # Simulate success message
        mqtt_client.receives(
            MockMQTTMessage(
                topic=MQTTTopics.ATTRIBUTES.value,
                payload=json.dumps(
                    {
                        MQTTSubTopics.DEPLOY_STATUS.value: {
                            "deploymentId": camera._state._to_deploy.deployment.deploymentId,
                            "reconcileStatus": "ok",
                        }
                    }
                ),
            )
        )

        ### Assert second phase: push the deployment
        await obs.wait_for()
        assert camera.current_state is DeployingAppCameraV2
        stage_cb.assert_awaited_once_with(DeployStage.WaitFirstStatus, ANY)
        stage_cb.reset_mock()

        # next step: triggering upon the next deployment status
        mqtt_client.receives(
            MockMQTTMessage(
                topic=MQTTTopics.ATTRIBUTES.value,
                payload=json.dumps(
                    {
                        MQTTSubTopics.DEPLOY_STATUS.value: {
                            "deploymentId": "immaterial",
                            "reconcileStatus": "ok",
                        }
                    }
                ),
            )
        )
        await obs.wait_for()
        stage_cb.assert_awaited_once_with(DeployStage.WaitAppliedConfirmation, ANY)
        stage_cb.reset_mock()
        mock_push_deploy.assert_awaited_once_with(
            mqtt_client.agent, OnWireProtocol.EVP2, target_manifest
        )
        mock_push_deploy.reset_mock()
        # The generated deploy ID for this phase is **equal to** that of the target deployment
        assert (
            camera._state._to_deploy.deployment.deploymentId
            == target_manifest.deployment.deploymentId
        )

        ### Assert third phase: deployment id matches the deployed one and reconcile is ok
        mqtt_client.receives(
            MockMQTTMessage(
                topic=MQTTTopics.ATTRIBUTES.value,
                payload=json.dumps(
                    {
                        MQTTSubTopics.DEPLOY_STATUS.value: {
                            "deploymentId": camera._state._to_deploy.deployment.deploymentId,
                            "reconcileStatus": "ok",
                        }
                    }
                ),
            )
        )
        await obs.wait_for()
        stage_cb.assert_awaited_once_with(DeployStage.Done, ANY)
        assert camera.current_state is ConfigureAppToRunning

        # final step: configure the edge app, then go back to the 'ready' state
        mock_push_deploy.reset_mock()
        mqtt_client.receives(
            MockMQTTMessage(
                topic=MQTTTopics.ATTRIBUTES.value,
                payload=json.dumps(
                    {
                        "state/node/edge_app": {
                            "res_info": {
                                "res_id": req_id,
                                "code": ResponseCode.OK,
                                "detail_msg": "",
                            }
                        }
                    }
                ),
            )
        )
        await obs.wait_for()
        mock_send_configuration.assert_awaited_once_with(
            "node",
            "edge_app",
            EdgeAppSpec(
                req_info=ReqInfo(req_id=req_id),
                common_settings=EdgeAppCommonSettings(
                    port_settings=EdgeAppPortSettings(
                        metadata=UploadSpec(enabled=False),
                        input_tensor=UploadSpec(enabled=False),
                    ),
                    process_state=ProcessState.RUNNING,
                ),
            ),
        )

        assert camera.current_state is ReadyCameraV2
        assert event_flag.is_set()
        error_cb.assert_not_called()
        mqtt_client.stop_receiving_messages()
        nursery.cancel_scope.cancel()


def test_deployment_setup(tmpdir, file_extension):
    mod_file = Path(tmpdir.join(f"a_module_file{file_extension}"))
    contents = str(uuid.uuid4())
    mod_file.write_text(contents)
    sha256_hash = hashlib.sha256()
    sha256_hash.update(contents.encode())
    mod_sha = sha256_hash.hexdigest()

    instance_name = "abc"
    spec = single_module_manifest_setup(instance_name, mod_file)

    computed_mod_name = f"{instance_name}-{mod_sha[:5]}"

    simple_gconf = GlobalConfigurationSampler(num_of_devices=1).sample()
    device_conf = simple_gconf.devices[0]

    port = 8888
    webserver = Mock()
    webserver.port = port
    webserver.url_root_at.return_value = f"http://configured_host:{port}"

    dm = spec.render_for_webserver(webserver, device_conf.id)

    assert instance_name in dm.deployment.instanceSpecs
    assert computed_mod_name in dm.deployment.modules
    assert dm.deployment.modules[computed_mod_name].hash == mod_sha
    assert (
        f"http://configured_host:{port}"
        in dm.deployment.modules[computed_mod_name].downloadUrl
    )
    assert str(port) in dm.deployment.modules[computed_mod_name].downloadUrl
    if file_extension == ModuleExtension.PY.as_suffix:
        assert dm.deployment.modules[computed_mod_name].moduleImpl == "python"
    else:
        assert dm.deployment.modules[computed_mod_name].moduleImpl == "wasm"


def template_deploy_status_for_deployment(raw_deployment: Deployment) -> dict[str, Any]:
    deploy_id = raw_deployment.deploymentId
    instances = list(raw_deployment.instanceSpecs.keys())
    modules = list(raw_deployment.modules.keys())
    return {
        "deploymentId": deploy_id,
        "reconcileStatus": "",
        "modules": {name: {"status": ""} for name in modules},
        "instances": {name: {"status": ""} for name in instances},
    }


def test_deployment_spec(tmp_path):

    ## Tests for collect_modules_from_pre

    # Simple case 0
    simple = DeploymentSpec.new_empty()
    simple.modules = {
        "mod0": Path("/wonderland/same-module"),
    }
    with pytest.raises(AssertionError):
        simple.collect_modules_from_pre()

    # Simple case 1
    module0 = tmp_path / "mod0"
    module0.touch()

    simple = DeploymentSpec.new_empty()
    simple.pre_deployment.modules = {
        "mod0": Module(
            downloadUrl=str(module0),
            entryPoint="",
            moduleImpl="",
            hash="",
        )
    }
    simple.collect_modules_from_pre()
    assert simple.modules == {"mod0": module0}

    # Error case 0
    simple = DeploymentSpec.new_empty()
    simple.pre_deployment.modules = {
        "modA": Module(
            downloadUrl="https://download.com/moduleA",
            entryPoint="",
            moduleImpl="",
            hash="",
        )
    }
    with pytest.raises(ValueError):
        simple.collect_modules_from_pre()
