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
from fastapi import status
from fastapi.testclient import TestClient

from tests.fixtures.configs import stored_devices
from tests.fixtures.fastapi import fa_client
from tests.strategies.samplers.configs import DeviceConnectionSampler


def test_health_check(fa_client: TestClient) -> None:

    # State prior to the call to DeviceServices.init_devices()
    # by the lifespan implementation
    assert not fa_client.app.state.device_service.started
    result = fa_client.get("/health")
    assert result.status_code == status.HTTP_425_TOO_EARLY

    expected_devices = DeviceConnectionSampler().list_of_samples()
    with stored_devices(expected_devices, fa_client.app.state.device_service):

        # After the lifespan has initialized all devices
        assert fa_client.app.state.device_service.started
        result = fa_client.get("/health")
        assert result.status_code == status.HTTP_200_OK
