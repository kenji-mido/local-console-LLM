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
from unittest.mock import MagicMock
from unittest.mock import Mock

import pytest
import trio
from local_console.core.camera.machine import Camera
from local_console.core.camera.states.v2.ready import ReadyCameraV2
from local_console.core.camera.v2.components.edge_app import APP_CONFIG_KEY
from local_console.core.camera.v2.components.edge_app import EdgeAppCommonSettings
from local_console.core.camera.v2.components.edge_app import EdgeAppPortSettings
from local_console.core.camera.v2.components.edge_app import EdgeAppSpec
from local_console.core.camera.v2.components.edge_app import ProcessState
from local_console.core.camera.v2.components.edge_app import UploadSpec
from local_console.core.camera.v2.components.req_res_info import ReqInfo
from local_console.core.schemas.schemas import DeviceConnection
from local_console.servers.webserver import FileInbox

from tests.mocks.http import mocked_http_server
from tests.mocks.http import MOCKED_WEBSERVER_PORT
from tests.mocks.method_extend import MethodObserver


@pytest.fixture
async def mocked_webserver():
    with mocked_http_server() as server:
        yield server


@pytest.fixture
async def ready_camera(
    single_device_config, mocked_webserver, mocked_agent_fixture, nursery
):
    config: DeviceConnection = single_device_config.devices[0]

    file_inbox = FileInbox(mocked_webserver)

    camera = Camera(
        config,
        MagicMock(spec=trio.MemorySendChannel),
        mocked_webserver,
        file_inbox,
        MagicMock(spec=trio.lowlevel.TrioToken),
        Mock(),
    )
    await nursery.start(camera.setup)
    await nursery.start(file_inbox.blobs_dispatch_task)
    await camera._transition_to_state(ReadyCameraV2(camera._common_properties))

    yield camera, config, mocked_agent_fixture, mocked_webserver

    mocked_agent_fixture.stop_receiving_messages()


@pytest.mark.trio
async def test_streaming_start_trigger(ready_camera, monkeypatch):
    from local_console.core.camera.states.v2.streaming import StreamingCameraV2

    camera, config, mocked_agent, mocked_server = ready_camera
    obs_exit = MethodObserver(monkeypatch)

    pub_mock = mocked_agent.agent.publish
    obs_exit.hook(ReadyCameraV2, "exit")

    spec = EdgeAppSpec(
        req_info=ReqInfo(req_id="reqid"),
        common_settings=EdgeAppCommonSettings(process_state=ProcessState.RUNNING),
    )
    # The user sends this via the API...
    await camera.send_configuration(
        "test-node", APP_CONFIG_KEY, spec.model_dump(exclude_none=True)
    )
    # ... and the state transition took place
    await obs_exit.wait_for()
    assert camera.current_state is StreamingCameraV2

    # Check what was sent to the device
    pub_mock.assert_awaited_once()
    payload = pub_mock.await_args.kwargs.get("payload")
    assert payload

    assert r"\"process_state\":2" in payload
    url = f"http://{config.mqtt.host}:{MOCKED_WEBSERVER_PORT}/{config.id}"
    assert url in payload

    # Now that we're here, test a file upload:
    state = camera._state
    obs_receive = MethodObserver(monkeypatch)
    obs_receive.hook(StreamingCameraV2, "_save_into_input_directory")
    assert sum(1 for _ in state.image_dir.iterdir()) == 0  # No images present
    assert sum(1 for _ in state.inference_dir.iterdir()) == 0  # No inferences present

    # When an image is received...
    await mocked_server.receives_file(
        f"/{config.id}/images/img0.jpg",
        b"data",
    )
    await obs_receive.wait_for()

    # ... it gets saved in the file system
    assert sum(1 for _ in state.image_dir.iterdir()) == 1
    assert sum(1 for _ in state.inference_dir.iterdir()) == 0

    # And when an inference is received...
    await mocked_server.receives_file(
        f"/{config.id}/inferences/md0.txt",
        b"data",
    )
    await obs_receive.wait_for()
    # ... it gets saved in the file system
    assert sum(1 for _ in state.image_dir.iterdir()) == 1
    assert sum(1 for _ in state.inference_dir.iterdir()) == 1


@pytest.mark.trio
async def test_streaming_stop_trigger(ready_camera, monkeypatch, caplog):
    from local_console.core.camera.states.v2.streaming import StreamingCameraV2

    camera, config, mocked_agent, mocked_server = ready_camera
    obs = MethodObserver(monkeypatch)

    pub_mock = mocked_agent.agent.publish
    mock_file_inbox = MagicMock(spec=FileInbox)
    mock_file_inbox.set_file_incoming_callable.return_value = ""
    camera._common_properties.file_inbox = mock_file_inbox

    obs.hook(StreamingCameraV2, "exit")

    # The test starts at the streaming state
    await camera._transition_to_state(
        StreamingCameraV2(
            camera._common_properties,
            "my-module",
            EdgeAppSpec(
                common_settings=EdgeAppCommonSettings(
                    process_state=ProcessState.RUNNING,
                    port_settings=EdgeAppPortSettings(
                        metadata=UploadSpec(enabled=True),
                        input_tensor=UploadSpec(enabled=True),
                    ),
                )
            ),
        )
    )

    pub_mock.reset_mock()
    spec = EdgeAppSpec(
        req_info=ReqInfo(req_id="reqid"),
        common_settings=EdgeAppCommonSettings(
            port_settings=EdgeAppPortSettings(
                metadata=UploadSpec(enabled=False),
                input_tensor=UploadSpec(enabled=False),
            )
        ),
    )
    # The user sends this via the API...
    await camera.send_configuration(
        "another-module", APP_CONFIG_KEY, spec.model_dump(exclude_none=True)
    )
    # ... and the state transition took place
    await obs.wait_for()
    assert camera.current_state is ReadyCameraV2
    mock_file_inbox.reset_file_incoming_callable.assert_called_once_with(config.id)

    # Check the warning emitted due to targeting a different module than the one
    # used for transitioning into the streaming state
    assert (
        "Stopped has been specified for module another-module, "
        "but streaming was initiated for module my-module"
    ) in caplog.text

    # Check what was sent to the device
    pub_mock.assert_awaited_once()
    payload = pub_mock.await_args.kwargs.get("payload")
    assert payload

    assert json.dumps(spec.model_dump_json(exclude_none=True)) in payload
