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
from local_console.utils.enums import StrEnum
from pydantic import BaseModel


class ProgressState(StrEnum):
    REQUEST_RECEIVED = "request_received"
    DOWNLOADING = "downloading"
    INSTALLING = "installing"
    DONE = "done"
    FAILED = "failed"
    FAILED_INVALID_ARGUMENT = "failed_invalid_argument"
    FAILED_TOKEN_EXPIRED = "failed_token_expired"
    FAILED_DOWNLOAD_RETRY_EXCEEDED = "failed_download_retry_exceeded"


class Target(BaseModel):
    component: int
    chip: str
    version: str
    progress: int | None = None
    process_state: ProgressState | None = None
    package_url: str
    hash: str
    size: int


class PrivateDeployFirmware(BaseModel):
    req_info: ReqInfo
    targets: list[Target]
    res_info: ResInfo | None = None
