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
import logging
from pathlib import PurePosixPath
from unittest.mock import Mock

import pytest
import requests
import trio
from httpx import AsyncClient
from local_console.core.schemas.schemas import DeviceID
from local_console.servers.webserver import AsyncWebserver
from local_console.servers.webserver import combine_url_components
from local_console.servers.webserver import FileInbox
from local_console.servers.webserver import SyncWebserver

from tests.mocks.config import set_configuration
from tests.strategies.samplers.configs import GlobalConfigurationSampler

logger = logging.getLogger(__name__)


def test_combine_url_components():
    expected = "http://host/here/we/go"

    assert combine_url_components("http://host/", "/here/we/go") == expected
    assert combine_url_components("http://host", "here/we/go") == expected
    assert combine_url_components("http://host", "here", "we/go") == expected


@pytest.fixture
def sync_webserver():
    with SyncWebserver() as server:
        yield server


def test_PUT_happy_path(sync_webserver):
    file_name = "testfile.txt"
    url = f"http://localhost:{sync_webserver.port}/{file_name}"
    data = b"This is a test file"

    recvd_data = b""
    recvd_path = ""

    def put_callback(data: bytes, path: str) -> None:
        nonlocal recvd_data, recvd_path
        recvd_data = data
        recvd_path = path

    sync_webserver.on_incoming = put_callback
    sync_webserver.max_upload_size = 1024

    # Upload file
    response = requests.put(url, data=data)
    assert response.status_code == 200

    # Verify the callback was effective
    assert recvd_data == data
    assert recvd_path == f"/{file_name}"


def test_PUT_size_limit_hit(sync_webserver):
    file_name = "testfile.txt"
    url = f"http://localhost:{sync_webserver.port}/{file_name}"
    data = b"This is a test file"

    content = b""

    def put_callback(data: bytes) -> None:
        nonlocal content
        content = data

    sync_webserver.on_incoming = Mock()
    sync_webserver.max_upload_size = 2

    # Upload file
    response = requests.put(url, data=data)
    assert response.status_code != 200

    # Verify the size limit was effective
    sync_webserver.on_incoming.assert_not_called()


def test_PUT_save_error(sync_webserver, caplog):
    file_name = "testfile.txt"
    url = f"http://localhost:{sync_webserver.port}/{file_name}"
    data = b"data"

    sync_webserver.on_incoming = Mock(side_effect=IOError("Some error"))

    response = requests.put(url, data=data)
    assert response.status_code == 200
    assert "Some error" in caplog.text


def test_PUT_callback_error(sync_webserver, caplog):
    file_name = "testfile.txt"
    url = f"http://localhost:{sync_webserver.port}/{file_name}"
    data = b"data"

    mock_callback = Mock(side_effect=IOError())
    sync_webserver.on_incoming = mock_callback

    response = requests.put(url, data=data)
    assert response.status_code == 200
    assert "Error while receiving data" not in caplog.text
    assert "Error while invoking callback" in caplog.text


def test_GET_file_not_found(sync_webserver):
    url = f"http://localhost:{sync_webserver.port}/not_enrolled_file"
    response = requests.get(url)
    assert response.status_code == 404


def test_GET_file_lifecycle(sync_webserver, tmp_path):
    file_name = "testfile.txt"
    file_path = tmp_path / file_name
    data = b"TF"
    file_path.write_bytes(data)

    sub_url = sync_webserver.enlist_file(file_path)
    url = f"http://localhost:{sync_webserver.port}/{sub_url}"

    response = requests.get(url)
    assert response.status_code == 200
    assert response.content == data

    sync_webserver.delist_file(file_path)
    response = requests.get(url)
    assert response.status_code == 404

    # Just to emphasize that "not found" does no longer mean
    # that the file is not present in the file system.
    assert file_path.exists()


def test_GET_http_range_full(sync_webserver, tmp_path):
    file_name = "testfile.txt"
    file_path = tmp_path / file_name
    data = b"This is a test file with range support."
    file_path.write_bytes(data)

    sub_url = sync_webserver.enlist_file(file_path)
    url = f"http://localhost:{sync_webserver.port}/{sub_url}"

    response = requests.get(url, headers={"Range": "bytes=0-"})
    assert response.status_code == 206
    assert response.content == data
    assert response.headers["Content-Range"] == f"bytes 0-{len(data)-1}/{len(data)}"
    assert response.headers["Accept-Ranges"] == "bytes"


def test_GET_http_range_partial(sync_webserver, tmp_path):
    file_name = "testfile.txt"
    file_path = tmp_path / file_name
    data = b"This is a test file with range support."
    file_path.write_bytes(data)

    sub_url = sync_webserver.enlist_file(file_path)
    url = f"http://localhost:{sync_webserver.port}/{sub_url}"

    response = requests.get(url, headers={"Range": "bytes=5-15"})
    assert response.status_code == 206
    assert response.content == data[5:16]
    assert response.headers["Content-Range"] == f"bytes 5-15/{len(data)}"


def test_GET_http_range_out_of_bounds(sync_webserver, tmp_path):
    file_name = "testfile.txt"
    file_path = tmp_path / file_name
    data = b"Short file."
    file_path.write_bytes(data)

    sub_url = sync_webserver.enlist_file(file_path)
    url = f"http://localhost:{sync_webserver.port}/{sub_url}"

    response = requests.get(url, headers={"Range": "bytes=100-200"})
    assert response.status_code == 416  # Range Not Satisfiable


def test_GET_no_range_headers_by_default(sync_webserver, tmp_path):
    file_name = "testfile.txt"
    file_path = tmp_path / file_name
    data = b"This is a test file with range support."
    file_path.write_bytes(data)

    sub_url = sync_webserver.enlist_file(file_path)
    url = f"http://localhost:{sync_webserver.port}/{sub_url}"

    response = requests.get(url)
    assert response.status_code == 200
    assert response.content == data
    assert "Content-Range" not in response.headers
    assert "Accept-Ranges" not in response.headers


@pytest.mark.trio
async def test_async_process_via_channel(nursery, tmp_path):
    received = trio.Event()

    async def webserver_loop(*, task_status=trio.TASK_STATUS_IGNORED):
        with trio.CancelScope() as cs:
            async with AsyncWebserver(port=0) as server:
                assert server.port
                task_status.started((server.port, cs))

                async for data, url_path in server.receive():
                    assert data == b"data"
                    assert url_path == "/testfile.txt"
                    received.set()

    port, cancel_scope = await nursery.start(webserver_loop)

    async with AsyncClient() as client:
        file_name = "testfile.txt"
        url = f"http://localhost:{port}/{file_name}"
        data = b"data"

        response = await client.put(url, content=data)
        assert response.status_code == 200
        await received.wait()
        cancel_scope.cancel()


def test_url_root_default_host():
    configuration = GlobalConfigurationSampler(num_of_devices=2).sample()
    set_configuration(configuration)
    devices = configuration.devices

    assert devices[0].mqtt.host == devices[1].mqtt.host

    with SyncWebserver() as server:
        root_for_0 = server.url_root_at(devices[0].id)
        root_for_1 = server.url_root_at(devices[1].id)

        assert root_for_0 == root_for_1
        assert root_for_0 == f"http://{devices[0].mqtt.host}:{server.port}/"


def test_url_root_non_default_host():
    configuration = GlobalConfigurationSampler(num_of_devices=2).sample()
    configuration.config.webserver.host = "15.14.13.12"
    set_configuration(configuration)
    devices = configuration.devices

    assert devices[0].mqtt.host == devices[1].mqtt.host

    with SyncWebserver() as server:
        root_for_0 = server.url_root_at(devices[0].id)
        root_for_1 = server.url_root_at(devices[1].id)

        assert root_for_0 == root_for_1
        assert root_for_0 == f"http://15.14.13.12:{server.port}/"


@pytest.mark.trio
async def test_file_inbox(nursery, tmp_path, caplog):
    configuration = GlobalConfigurationSampler(num_of_devices=1).sample()
    configuration.devices[0].mqtt.host = "localhost"
    set_configuration(configuration)

    should_finish = trio.Event()
    received = trio.Event()

    async def webserver_loop(*, task_status=trio.TASK_STATUS_IGNORED):
        async with AsyncWebserver(port=0) as server:
            assert server
            task_status.started(server)

            await should_finish.wait()
            return

    server = await nursery.start(webserver_loop)
    url_root = f"http://localhost:{server.port}/"

    inbox = FileInbox(server)
    await nursery.start(inbox.blobs_dispatch_task)

    test_target = configuration.devices[0].id
    test_file_name = "testfile.txt"
    test_data = b"data"

    async def test_blob_function(data: bytes, url: str) -> None:
        assert data == test_data
        assert DeviceID(int(PurePosixPath(url).parts[1])) == test_target
        received.set()

    async with AsyncClient() as client:

        # Test an incoming file without a target prefix
        url = f"{url_root}{test_file_name}"
        response = await client.put(url, content=test_data)
        assert response.status_code == 200
        assert (
            f"Received blob at path /{test_file_name} without a target prefix."
            in caplog.text
        )

        # Test an incoming file for a target prefix without registered function
        unknown_prefix = 11111
        url = f"{url_root}{unknown_prefix}/{test_file_name}"
        response = await client.put(url, content=test_data)
        assert response.status_code == 200
        assert (
            f"Received blob at path /{unknown_prefix}/{test_file_name} which has no function registered."
            in caplog.text
        )

        # Test an incoming file with a registered function
        upload_root = inbox.set_file_incoming_callable(test_target, test_blob_function)
        assert upload_root == f"{url_root}{test_target}"

        url = f"{upload_root}/{test_file_name}"
        response = await client.put(url, content=test_data)
        assert response.status_code == 200
        await received.wait()

        # Test function over-registration
        with pytest.raises(
            AssertionError, match="already has a registered blob function."
        ):
            inbox.set_file_incoming_callable(test_target, test_blob_function)

        # Test function de-registration
        inbox.reset_file_incoming_callable(test_target)
        response = await client.put(url, content=test_data)  # Same URL as previous case
        assert response.status_code == 200
        assert (
            f"Received blob at path /{unknown_prefix}/{test_file_name} which has no function registered."
            in caplog.text
        )

        should_finish.set()
