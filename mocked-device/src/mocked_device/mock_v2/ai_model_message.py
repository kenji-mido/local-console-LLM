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
from enum import IntEnum
from enum import StrEnum
from typing import Any
from typing import Optional

from mocked_device.mock_v2.ea_config import ReqInfo
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator


# Enum for process state
class ProcessStateEnum(StrEnum):
    request_received = "request_received"
    downloading = "downloading"
    installing = "installing"
    done = "done"
    failed = "failed"
    failed_invalid_argument = "failed_invalid_argument"
    failed_token_expired = "failed_token_expired"
    failed_download_retry_exceeded = "failed_download_retry_exceeded"


# Enum for result codes
class ResultCodeEnum(IntEnum):
    ok = 0
    cancelled = 1
    unknown = 2
    invalid_argument = 3
    deadline_exceeded = 4
    not_found = 5
    already_exists = 6
    permission_denied = 7
    resource_exhausted = 8
    failed_precondition = 9
    aborted = 10
    out_of_range = 11
    unimplemented = 12
    internal = 13
    unavailable = 14
    data_loss = 15
    unauthenticated = 16


# Schema for targets
class Target(BaseModel):
    chip: Optional[str] = Field(None, max_length=32)
    version: Optional[str] = Field(None, max_length=44)
    progress: Optional[int] = Field(None, ge=0, le=100)
    process_state: Optional[ProcessStateEnum] = ProcessStateEnum.request_received
    package_url: Optional[str] = Field(None, max_length=320)
    hash: Optional[str] = Field(None, max_length=44)
    size: Optional[int]


# Schema for res_info
class ResInfo(BaseModel):
    res_id: str = ""
    code: ResultCodeEnum = ResultCodeEnum.ok
    detail_msg: Optional[str] = None


# Main schema for PRIVATE_deploy_ai_model
class DeployAiModel(BaseModel):
    req_info: ReqInfo = Field(default=ReqInfo(req_id=""), alias="req_info")
    targets: list[Target] = Field(default=[], alias="targets")
    res_info: ResInfo = Field(default=ResInfo(), alias="res_info")

    model_config = ConfigDict(validate_assignment=True, populate_by_name=True)

    @field_validator(
        "req_info",
        "targets",
        "res_info",
        mode="before",
    )
    @classmethod
    def to_dict(cls, data: Any) -> Any:
        # Device reports attributes as strings. This method converts the string into a JSON.
        if isinstance(data, str):
            return json.loads(data)
        return data
