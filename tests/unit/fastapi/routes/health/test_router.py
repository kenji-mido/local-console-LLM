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
import pytest
from fastapi import status
from httpx import AsyncClient

from tests.fixtures.devices import stored_devices
from tests.strategies.samplers.configs import DeviceConnectionSampler


@pytest.mark.trio
async def test_health_check(fa_client_async: AsyncClient) -> None:

    device_service = fa_client_async._transport.app.state.device_service
    # State prior to the call to DeviceServices.init_devices()
    # by the lifespan implementation
    assert not device_service.started
    result = await fa_client_async.get("/health")
    assert result.status_code == status.HTTP_425_TOO_EARLY

    expected_devices = DeviceConnectionSampler().list_of_samples()
    async with stored_devices(expected_devices, device_service):

        # After the lifespan has initialized all devices
        assert device_service.started
        result = await fa_client_async.get("/health")
        assert result.status_code == status.HTTP_200_OK
