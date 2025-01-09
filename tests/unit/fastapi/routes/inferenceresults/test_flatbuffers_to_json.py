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
from urllib.parse import quote

from fastapi import status
from fastapi.testclient import TestClient
from local_console.core.camera.enums import ApplicationType

from tests.fixtures.configs import stored_devices
from tests.fixtures.fastapi import fa_client
from tests.strategies.samplers.configs import DeviceConnectionSampler

# Extracted from a real inference result
FLATBUFFERS = (
    "DAAAAAAABgAKAAQABgAAAAwAAAAAAAYACAAEAAYAAAAEAAAABQAAAFAAAAA4AAAAKAAAABwAAAAEAAAAz"
    "P///wIAAAAAAKA9CAAIAAAABAAIAAAAAAAsPuj///8EAAAAAABAPvT///8BAAAAAABcPggADAAEAAgACA"
    "AAAAMAAAAAALQ+"
)


def get_device_and_id():
    expected_devices = DeviceConnectionSampler().list_of_samples(length=1)
    device = expected_devices[0]
    device_id = device.mqtt.port
    return expected_devices, device_id


def test_convert_to_json(fa_client: TestClient) -> None:
    expected_devices, device_id = get_device_and_id()
    with stored_devices(expected_devices, fa_client.app.state.device_service):
        result = fa_client.patch(
            f"/devices/{device_id}/configuration",
            json={"vapp_type": str(ApplicationType.CLASSIFICATION)},
        )
        assert result.status_code == status.HTTP_200_OK

        result = fa_client.get(
            f"/inferenceresults/devices/{device_id}/json?flatbuffer_payload={quote(FLATBUFFERS)}",
        )
        assert result.status_code == status.HTTP_200_OK
        assert result.json() == {
            "perception": {
                "classification_list": [
                    {"class_id": 3, "score": 0.351562},
                    {"class_id": 1, "score": 0.214844},
                    {"class_id": 4, "score": 0.1875},
                    {"class_id": 0, "score": 0.167969},
                    {"class_id": 2, "score": 0.078125},
                ]
            }
        }


def test_convert_to_json_device_missing(fa_client: TestClient) -> None:
    result = fa_client.get(
        f"/inferenceresults/devices/1883/json?flatbuffer_payload={quote(FLATBUFFERS)}",
    )
    assert result.status_code == status.HTTP_404_NOT_FOUND


def test_convert_to_json_configuration_missing(fa_client: TestClient) -> None:
    expected_devices, device_id = get_device_and_id()
    with stored_devices(expected_devices, fa_client.app.state.device_service):
        result = fa_client.get(
            f"/inferenceresults/devices/{device_id}/json?flatbuffer_payload={quote(FLATBUFFERS)}",
        )
        assert result.status_code == status.HTTP_404_NOT_FOUND
        assert result.json()["message"] == "Device schema not configured"
