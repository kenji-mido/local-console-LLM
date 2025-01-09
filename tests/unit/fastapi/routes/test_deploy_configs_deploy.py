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
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import pytest
import trio
from local_console.core.camera.enums import OTAUpdateStatus
from local_console.core.deploy_config import DeployConfig
from local_console.core.deploy_config import DeployConfigManager
from local_console.core.device_services import DeviceServices
from local_console.core.edge_apps import EdgeAppsManager
from local_console.core.files.files import FilesManager
from local_console.core.files.values import FileType
from local_console.core.firmwares import FirmwareManager
from local_console.core.models import ModelManager
from local_console.core.schemas.schemas import DeviceConnection
from local_console.utils.validation import AOT_XTENSA_HEADER
from local_console.utils.validation import IMX500_MODEL_HEADER

from tests.fixtures.agent import mocked_agent_fixture
from tests.fixtures.agent import MockedIOs
from tests.fixtures.agent import running_servers
from tests.fixtures.fastapi import fa_client_with_agent
from tests.fixtures.firmware import mock_get_ota_update_status
from tests.mocks.mock_paho_mqtt import MockMqttAgent
from tests.strategies.samplers.configs import DeviceConnectionSampler
from tests.strategies.samplers.files import DeployConfigInSampler
from tests.strategies.samplers.files import FirmwareInSampler
from tests.strategies.samplers.files import PostEdgeAppsRequestInSampler
from tests.strategies.samplers.files import PostModelsInSampler
from tests.strategies.samplers.mqtt_message import MockMQTTMessage
from tests.unit.core.deploy.tasks.test_app_task import _get_id


class DeployContext:
    def __init__(
        self, device: DeviceConnection, config: DeployConfig, servers: MockedIOs
    ) -> None:
        self.device = device
        self.config = config
        self.servers = servers


@asynccontextmanager
async def deploy_context(
    fa_client_with_agent: Any,
) -> AsyncGenerator[DeployContext, None]:
    app = fa_client_with_agent._transport.app
    app_state = app.state
    # force load managers
    result = await fa_client_with_agent.post(
        "/deploy_configs/not_found/apply", json={"invalid": "json"}
    )

    assert result.status_code == 422
    async with running_servers() as servers:
        device = DeviceConnectionSampler().sample()
        device_service: DeviceServices = app_state.device_service
        device_service.states[device.mqtt.port] = servers.state
        file_manager: FilesManager = app_state.file_manager
        firmware_file_info = file_manager.add_file(
            FileType.FIRMWARE, "file.fpk", b"Sample content"
        )
        app_file_info = file_manager.add_file(
            FileType.APP, "app.bin", bytes(AOT_XTENSA_HEADER) + b"new content"
        )
        file_content = bytearray(64)
        file_content[0 : len(IMX500_MODEL_HEADER)] = IMX500_MODEL_HEADER
        file_content[0x30:0x40] = b"000000000000000"
        model_file_info = file_manager.add_file(
            FileType.MODEL, "model.fpk", file_content
        )
        firmware_manager: FirmwareManager = app_state.firmware_manager
        firmware_manager.register(
            FirmwareInSampler(file_id=firmware_file_info.id).sample()
        )
        app_manager: EdgeAppsManager = app_state.edge_apps_manager
        app_manager.register(
            PostEdgeAppsRequestInSampler(edge_app_id=app_file_info.id).sample()
        )
        model_manager: ModelManager = app_state.model_manager
        model_in = PostModelsInSampler(model_file_id=model_file_info.id).sample()
        model_manager.register(model_in)
        config_in = DeployConfigInSampler(
            fw_ids=[firmware_file_info.id],
            edge_app_ids=[app_file_info.id],
            model_ids=[model_in.model_id],
        ).sample()
        config_manager: DeployConfigManager = app_state.deploy_config_manager
        config_manager.register(config_in)
        with mock_get_ota_update_status(
            [OTAUpdateStatus.DONE, OTAUpdateStatus.UPDATING, OTAUpdateStatus.DONE]
        ):
            yield DeployContext(
                device=device,
                config=config_manager.get_by_id(config_in.config_id),
                servers=servers,
            )


@pytest.mark.trio
async def test_deploy(
    fa_client_with_agent,
    mocked_agent_fixture: MockMqttAgent,
) -> None:
    assert mocked_agent_fixture
    async with deploy_context(fa_client_with_agent) as context:

        result = await fa_client_with_agent.post(
            f"/deploy_configs/{context.config.config_id}/apply",
            json={
                "device_ids": [str(context.device.mqtt.port)],
                "description": "Is ignored",
            },
        )

        assert result.status_code == 200

        # All the elements are being deployed
        result = await fa_client_with_agent.get("/deploy_history")

        assert result.status_code == 200
        deployed = result.json()["deploy_history"][0]
        assert deployed["deploy_type"] == "ConfigTask"
        assert deployed["deploying_cnt"] == 3
        # Device send firmware is deployed
        for i in range(40):
            msg = MockMQTTMessage.config_status(sensor_id=f"100A50{i}")
            context.servers.mqtt.send_messages([msg])
            result = await fa_client_with_agent.get("/deploy_history")
            deployed = result.json()["deploy_history"][0]
            if deployed["success_cnt"] == 0:
                await trio.sleep(0.05)
            else:
                break

        assert deployed["deploying_cnt"] == 2
        assert deployed["success_cnt"] == 1
        # Device send app is deployed
        for _ in range(40):
            find_the_id = _get_id(context.servers.state)
            msg = MockMQTTMessage.update_status(deployment_id=find_the_id)
            context.servers.mqtt.send_messages([msg])
            result = await fa_client_with_agent.get("/deploy_history")
            deployed = result.json()["deploy_history"][0]
            if deployed["success_cnt"] == 1:
                await trio.sleep(0.05)
            else:
                break
        assert deployed["deploying_cnt"] == 1
        assert deployed["success_cnt"] == 2

        # Device send module is deployed
        for i in range(40):
            msg = MockMQTTMessage.config_status(
                sensor_id=f"000A50{i}", dnn_model_version=[]
            )
            context.servers.mqtt.send_messages([msg])
            await trio.sleep(0.05)
            msg = MockMQTTMessage.config_status(
                sensor_id=f"100A50{i}", dnn_model_version=["0308000000000100"]
            )
            context.servers.mqtt.send_messages([msg])
            result = await fa_client_with_agent.get("/deploy_history")
            deployed = result.json()["deploy_history"][0]
            if deployed["success_cnt"] == 2:
                await trio.sleep(0.05)
            else:
                break
        assert deployed["deploying_cnt"] == 0
        assert deployed["success_cnt"] == 3


@pytest.mark.trio
async def test_deploy_invalid_ints(
    fa_client_with_agent,
    mocked_agent_fixture: MockMqttAgent,
) -> None:
    result = await fa_client_with_agent.post(
        "/deploy_configs/ignored/apply",
        json={
            "device_ids": ["not", "an", "int"],
            "description": "Is ignored",
        },
    )

    assert result.status_code == 422
    assert result.json()["result"] == "ERROR"
    assert (
        result.json()["message"]
        == "device_ids.0: Input should be a valid integer, unable to parse string as an integer and device_ids.1: Input should be a valid integer, unable to parse string as an integer and device_ids.2: Input should be a valid integer, unable to parse string as an integer"
    )


@pytest.mark.trio
async def test_deploy_two_times_one_edge_app_pending(
    fa_client_with_agent,
    mocked_agent_fixture: MockMqttAgent,
) -> None:
    assert mocked_agent_fixture
    async with deploy_context(fa_client_with_agent) as context:

        result = await fa_client_with_agent.post(
            f"/deploy_configs/{context.config.config_id}/apply",
            json={
                "device_ids": [str(context.device.mqtt.port)],
                "description": "Is ignored",
            },
        )

        # Device send firmware is deployed
        for i in range(40):
            msg = MockMQTTMessage.config_status(sensor_id=f"100A50{i}")
            context.servers.mqtt.send_messages([msg])
            result = await fa_client_with_agent.get("/deploy_history")
            deployed = result.json()["deploy_history"][0]
            if deployed["success_cnt"] == 0:
                await trio.sleep(0.05)
            else:
                break
        # One edgeapp is running
        result = await fa_client_with_agent.get("/deploy_history")

        assert result.status_code == 200
        edge_app = result.json()["deploy_history"][0]["edge_apps"][0]
        assert edge_app["status"] == "Deploying"

        result = await fa_client_with_agent.post(
            f"/deploy_configs/{context.config.config_id}/apply",
            json={
                "device_ids": [str(context.device.mqtt.port)],
                "description": "Is ignored",
            },
        )
        assert result.status_code == 409
        assert result.json()["result"] == "ERROR"
        assert (
            result.json()["message"] == "Another task is already running on the device"
        )
        assert result.json()["code"] == "110001"
        # One edgeapp is running the other one is failed
        result = await fa_client_with_agent.get("/deploy_history")

        assert result.status_code == 200
        edge_app1 = result.json()["deploy_history"][0]["edge_apps"][0]
        assert edge_app1["status"] == "Deploying"

        assert len(result.json()["deploy_history"]) == 1
        assert len(result.json()["deploy_history"][0]["edge_apps"]) == 1
        assert len(result.json()["deploy_history"][0]["models"]) == 1


@pytest.mark.trio
async def test_deploy_while_ongoing_deployment(
    fa_client_with_agent,
    mocked_agent_fixture: MockMqttAgent,
) -> None:
    assert mocked_agent_fixture
    async with deploy_context(fa_client_with_agent) as context:
        # Make sure there are no deployments before starting
        result = await fa_client_with_agent.get("/deploy_history")
        assert result.status_code == 200
        assert len(result.json()["deploy_history"]) == 0

        # Add a deployment
        await fa_client_with_agent.post(
            f"/deploy_configs/{context.config.config_id}/apply",
            json={
                "device_ids": [str(context.device.mqtt.port)],
                "description": "Is ignored",
            },
        )

        # Make sure the previous deployment has been properly registered
        result = await fa_client_with_agent.get("/deploy_history")
        assert result.status_code == 200
        assert len(result.json()["deploy_history"]) == 1
        assert len(result.json()["deploy_history"][0]["edge_apps"]) == 1
        assert len(result.json()["deploy_history"][0]["models"]) == 1

        # Add a second deployment while the first is being processed
        result = await fa_client_with_agent.post(
            f"/deploy_configs/{context.config.config_id}/apply",
            json={
                "device_ids": [str(context.device.mqtt.port)],
                "description": "Is ignored",
            },
        )
        assert result.status_code == 409
        assert result.json()["result"] == "ERROR"
        assert (
            result.json()["message"] == "Another task is already running on the device"
        )
        assert result.json()["code"] == "110001"

        result = await fa_client_with_agent.get("/deploy_history")
        assert result.status_code == 200
        assert len(result.json()["deploy_history"]) == 1
        assert len(result.json()["deploy_history"][0]["edge_apps"]) == 1
        assert len(result.json()["deploy_history"][0]["models"]) == 1
