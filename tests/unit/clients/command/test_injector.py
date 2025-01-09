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
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from local_console.clients.command.rpc_injector import ChainedRPCInjector
from local_console.clients.command.rpc_injector import StartStreamingInjector
from local_console.core.camera.state import CameraState

from tests.fixtures.camera import cs_init
from tests.mocks.mock_configs import config_without_io
from tests.strategies.samplers.configs import GlobalConfigurationSampler
from tests.strategies.samplers.deploy import RPCArgumentSampler


@pytest.mark.trio
async def test_inject_start_streaming(cs_init) -> None:
    camera_state = cs_init
    camera_state.mqtt_client = AsyncMock()

    simple_gconf = GlobalConfigurationSampler(num_of_devices=1).sample()
    device_conf = simple_gconf.devices[0]
    device_conf.webserver.host = "http_server"
    with (
        config_without_io(simple_gconf),
        patch(
            "local_console.core.camera.mixin_streaming.config_obj.get_device_config",
            return_value=device_conf,
        ) as mock_device_config,
    ):
        param = RPCArgumentSampler(method="StartUploadInferenceData").sample()
        camera_state.upload_port = 8123

        injector = StartStreamingInjector(camera_state)

        result = injector.inject(param)
        assert result.params["StorageName"] == "http://http_server:8123"
        assert result.params["StorageSubDirectoryPath"] == "images"
        assert result.params["StorageNameIR"] == "http://http_server:8123"
        assert result.params["StorageSubDirectoryPathIR"] == "inferences"
        assert result.params["CropHOffset"] == 0
        assert result.params["CropVOffset"] == 0
        assert result.params["CropHSize"] == 4056
        assert result.params["CropVSize"] == 3040
        mock_device_config.assert_called()


@pytest.mark.trio
async def test_inject_start_stream_keep_values(cs_init) -> None:
    camera_state = cs_init
    camera_state.mqtt_client = AsyncMock()

    simple_gconf = GlobalConfigurationSampler(num_of_devices=1).sample()
    device_conf = simple_gconf.devices[0]
    device_conf.webserver.host = "http_server"
    with (
        config_without_io(simple_gconf),
        patch(
            "local_console.core.camera.mixin_streaming.config_obj.get_device_config",
            return_value=device_conf,
        ) as mock_device_config,
        patch(
            "local_console.core.camera.mixin_streaming.get_webserver_ip",
            return_value="http_server",
        ),
    ):
        param = RPCArgumentSampler(method="StartUploadInferenceData").sample()
        param.params = {
            "StorageName": "http://test:1234",
            "StorageSubDirectoryPath": "other",
            "StorageNameIR": "http://test2:1234",
            "StorageSubDirectoryPathIR": "another",
            "CropHOffset": 100,
            "CropVOffset": 100,
            "CropHSize": 500,
            "CropVSize": 500,
        }
        camera_state.upload_port = 8123

        injector = StartStreamingInjector(camera_state)

        result = injector.inject(param)
        assert result.params["StorageName"] == "http://test:1234"
        assert result.params["StorageSubDirectoryPath"] == "other"
        assert result.params["StorageNameIR"] == "http://test2:1234"
        assert result.params["StorageSubDirectoryPathIR"] == "another"
        assert result.params["CropHOffset"] == 100
        assert result.params["CropVOffset"] == 100
        assert result.params["CropHSize"] == 500
        assert result.params["CropVSize"] == 500
        mock_device_config.assert_called()


def test_inject_ignore_on_incorrectMethod() -> None:
    with patch(
        "local_console.core.camera.mixin_streaming.get_webserver_ip",
        return_value="http_server",
    ):
        param = RPCArgumentSampler(params={}, method="incorrectMethod").sample()
        camera_state = CameraState(MagicMock(), MagicMock())
        camera_state.upload_port = 8123

        injector = StartStreamingInjector(camera_state)

        result = injector.inject(param)
        assert result.params == {}


def test_chained_injectors() -> None:
    injector1 = MagicMock()
    injector2 = MagicMock()

    input = RPCArgumentSampler(params={"in": "put"}).sample()
    intermediate = RPCArgumentSampler(params={"in": "termediate"}).sample()
    expected = RPCArgumentSampler(params={"ex": "pected"}).sample()
    injector1.inject.return_value = intermediate
    injector2.inject.return_value = expected

    injector = ChainedRPCInjector([injector1, injector2])

    result = injector.inject(input)

    injector1.inject.assert_called_once_with(input)
    injector2.inject.assert_called_once_with(intermediate)

    assert result is expected
