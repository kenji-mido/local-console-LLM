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
from collections.abc import AsyncGenerator
from unittest.mock import ANY
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest
import trio
from local_console.core.camera.enums import MQTTTopics
from local_console.core.camera.machine import Camera
from local_console.core.camera.states.v2.deployment import DeployingAppCameraV2
from local_console.core.commands.deploy import DeploymentSpec
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.servers.webserver import SyncWebserver

from tests.mocks.http import MOCKED_WEBSERVER_PORT
from tests.mocks.method_extend import MethodObserver
from tests.mocks.mock_paho_mqtt import MockMqttAgent
from tests.strategies.samplers.mqtt_message import MockMQTTMessage


def issue_reply_message(req_id: str, targets=[]) -> MockMQTTMessage:
    return MockMQTTMessage(
        topic=MQTTTopics.ATTRIBUTES.value,
        payload=json.dumps(
            {
                "state/$system/PRIVATE_deploy_ai_model": json.dumps(
                    {
                        "req_info": {"req_id": req_id},
                        "targets": targets,
                        "res_info": {"res_id": req_id, "code": 0, "detail_msg": "ok"},
                    }
                )
            }
        ),
    )


@pytest.fixture
async def ready_v2_camera(
    camera, mocked_agent_fixture, single_device_config, nursery
) -> AsyncGenerator[[Camera, MockMqttAgent, trio.Nursery], None]:
    """
    Set starting state up for a camera instance with mocked messaging
    """
    with (patch("local_console.core.camera.states.base.spawn_broker"),):
        from local_console.core.camera.states.v2.ready import ReadyCameraV2

        state_props = camera._common_properties
        await nursery.start(camera.setup)
        start_state = ReadyCameraV2(state_props)
        await camera._transition_to_state(start_state)

        assert camera.current_state is ReadyCameraV2
        yield camera, mocked_agent_fixture, nursery


@pytest.mark.trio
async def test_deploy_sensor_model(
    ready_v2_camera: tuple[Camera, MockMqttAgent, trio.Nursery],
    monkeypatch,
    tmp_path,
) -> None:
    camera, mqtt_client, nursery = ready_v2_camera
    obs = MethodObserver(monkeypatch)

    package_file = tmp_path / "dummy.bin"
    package_file.write_bytes(b"some (not) random bytes")

    with (
        patch("local_console.core.camera.states.v2.ota_sensor.TimeoutBehavior"),
        patch("local_console.core.camera.states.v2.deployment.TimeoutBehavior"),
        patch(
            "local_console.core.camera.states.v2.common.ConnectedCameraStateV2.send_configuration"
        ) as mock_send_config,
        patch(
            "local_console.core.camera.states.v2.deployment.publish_deploy"
        ) as mock_publish_deploy,
    ):
        from local_console.core.camera.states.v2.ota_sensor import (
            ClearingAppCameraThenUndeployModelV2,
            ClearingSensorModelThenDeployModelV2,
            UpdateSensorThenDeployAppV2,
        )

        # This setup helps awaiting for message processing
        obs.hook(ClearingAppCameraThenUndeployModelV2, "on_message_received")
        obs.hook(ClearingSensorModelThenDeployModelV2, "on_message_received")
        obs.hook(UpdateSensorThenDeployAppV2, "on_message_received")

        # Pretend the camera has some models pre-loaded
        state_props = camera._common_properties
        state_props.reported.dnn_versions = ["a", "b", "c", ""]

        # Start model deployment state sequence
        await camera.deploy_sensor_model(package_file, trio.Event(), AsyncMock(), 4, 8)

        # Step 1: Undeploy edge app
        assert camera.current_state is ClearingAppCameraThenUndeployModelV2
        mock_publish_deploy.assert_called_once_with(
            ANY, OnWireProtocol.EVP2, camera._state._to_deploy
        )

        mqtt_client.receives(
            MockMQTTMessage(
                topic=MQTTTopics.ATTRIBUTES.value,
                payload=json.dumps(
                    {
                        "deploymentStatus": {
                            "instances": {},
                            "modules": {},
                            "deploymentId": camera._state._to_deploy.deployment.deploymentId,
                            "reconcileStatus": "ok",
                        }
                    }
                ),
            )
        )
        await obs.wait_for()

        # Step 2: Undeploy model
        assert camera.current_state is ClearingSensorModelThenDeployModelV2

        assert camera._state.last_model_count == 3
        req_id = camera._state.req_id.req_id

        # Model clearing command issued during the `enter` transition into the state
        mock_send_config.assert_awaited_once_with(
            "$system",
            "PRIVATE_deploy_ai_model",
            {"req_info": {"req_id": req_id}, "targets": []},
        )
        mock_send_config.reset_mock()

        # Receive ACK for the command, but the pre-loaded models still remain
        mqtt_client.receives(issue_reply_message(req_id))
        await obs.wait_for()

        # Now pretend the models have been cleared
        state_props.reported.dnn_versions = ["", "", "", ""]

        # Next status update...
        mqtt_client.receives(issue_reply_message(req_id))
        await obs.wait_for()

        # ... should have caused transition to the next state

        # Step 3: Deploy AI Model
        assert camera.current_state is UpdateSensorThenDeployAppV2
        req_id = camera._state.req_id.req_id

        camera._common_properties.reported.latest_deployment_spec = (
            DeploymentSpec.new_empty()
        )

        mqtt_client.receives(
            issue_reply_message(
                req_id,
                [
                    {
                        "chip": "this is ignored",
                        "version": "this is ignored",
                        "package_url": "this is ignored",
                        "hash": "this is ignored",
                        "size": 1234,
                        "progress": 100,
                        "process_state": "done",
                    }
                ],
            )
        )
        await obs.wait_for()

        # Step 4: Deploy Edge App
        assert camera.current_state is DeployingAppCameraV2

        # End of this test. To avoid hanging, transition back to ready.
        mqtt_client.stop_receiving_messages()
        from local_console.core.camera.states.v2.ready import ReadyCameraV2

        await camera._transition_to_state(ReadyCameraV2(state_props))


@pytest.mark.trio
async def test_update_sensor_model_camera_v2(
    ready_v2_camera: tuple[Camera, MockMqttAgent, trio.Nursery],
    monkeypatch,
    tmp_path,
) -> None:
    camera, mqtt_client, nursery = ready_v2_camera
    obs = MethodObserver(monkeypatch)

    package_file = tmp_path / "dummy.bin"
    package_file.write_bytes(b"some (not) random bytes")
    mocked_package_version = "CAFE"
    mocked_package_hash = "such-secure-very-integrity"

    with (
        patch(
            "local_console.core.camera.states.v2.ota_sensor.get_package_version",
            return_value=mocked_package_version,
        ),
        patch(
            "local_console.core.camera.states.v2.ota_sensor.get_package_hash",
            return_value=mocked_package_hash,
        ),
        patch("local_console.core.camera.states.v2.ota_sensor.TimeoutBehavior"),
        patch(
            "local_console.core.camera.states.v2.common.ConnectedCameraStateV2.send_configuration"
        ) as mock_send_config,
    ):
        from local_console.core.camera.states.v2.ota_sensor import (
            UpdateSensorModelCameraV2,
        )
        from local_console.core.camera.states.v2.ready import ReadyCameraV2

        # This setup helps awaiting for message processing
        obs.hook(UpdateSensorModelCameraV2, "on_message_received")

        # Precondition from ClearingSensorModelCameraV2
        state_props = camera._common_properties
        state_props.reported.dnn_versions = ["", "", "", ""]

        # Start model deployment state sequence
        start_state = UpdateSensorModelCameraV2(
            state_props, package_file, trio.Event(), AsyncMock(), 8
        )
        await camera._transition_to_state(start_state)
        req_id = camera._state.req_id.req_id

        url_path = SyncWebserver.url_path_for(package_file)

        # Used for assertions from now on
        base_target_body = {
            "chip": "sensor_chip",
            "version": mocked_package_version,
            "package_url": f"http://mqtt.server:{MOCKED_WEBSERVER_PORT}{url_path}",
            "hash": mocked_package_hash,
            "size": package_file.stat().st_size,
        }

        # Model clearing command issued during the `enter` transition into the state
        mock_send_config.assert_awaited_once_with(
            "$system",
            "PRIVATE_deploy_ai_model",
            {"targets": [base_target_body], "req_info": {"req_id": req_id}},
        )
        mock_send_config.reset_mock()

        # Receive ACK for the command, with some progress update
        progress = [
            dict(progress=0, process_state="request_received", **base_target_body)
        ]
        mqtt_client.receives(issue_reply_message(req_id, progress))
        await obs.wait_for()

        # more progress updates
        progress = [dict(progress=25, process_state="downloading", **base_target_body)]
        mqtt_client.receives(issue_reply_message(req_id, progress))
        await obs.wait_for()

        # more progress updates
        progress = [dict(progress=50, process_state="downloading", **base_target_body)]
        mqtt_client.receives(issue_reply_message(req_id, progress))
        await obs.wait_for()

        # more progress updates
        progress = [dict(progress=75, process_state="installing", **base_target_body)]
        mqtt_client.receives(issue_reply_message(req_id, progress))
        await obs.wait_for()

        # Next status update...
        progress = [dict(progress=100, process_state="done", **base_target_body)]
        mqtt_client.receives(issue_reply_message(req_id, progress))
        await obs.wait_for()

        # ... should have caused transition back to the ready state
        assert camera.current_state is ReadyCameraV2
