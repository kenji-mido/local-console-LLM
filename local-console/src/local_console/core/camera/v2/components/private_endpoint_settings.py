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
from local_console.core.camera.v2.components.req_res_info import ReqInfo
from local_console.core.camera.v2.components.req_res_info import ResInfo
from pydantic import BaseModel


class PrivateEndpointSettings(BaseModel):
    req_info: ReqInfo
    endpoint_url: str
    endpoint_port: int
    protocol_version: str
    res_info: ResInfo
