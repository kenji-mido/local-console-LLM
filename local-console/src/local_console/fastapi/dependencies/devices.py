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
from typing import Annotated

import trio
from fastapi import Depends
from fastapi import FastAPI
from fastapi import Request
from local_console.core.device_services import DeviceServices


def add_device_service(app: FastAPI, nursery: trio.Nursery) -> None:
    if not hasattr(app.state, "device_service"):
        send, _ = trio.open_memory_channel(0)
        token = trio.lowlevel.current_trio_token()
        app.state.device_service = DeviceServices(nursery, send, token)


def device_service_from_app(app: FastAPI) -> DeviceServices:
    assert isinstance(app.state.device_service, DeviceServices)
    return app.state.device_service


def device_service(request: Request) -> DeviceServices:
    return device_service_from_app(request.app)


InjectDeviceServices = Annotated[DeviceServices, Depends(device_service)]
