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
from datetime import datetime

from local_console.core.deploy.tasks.app_task import AppDeployHistoryInfo
from local_console.core.deploy.tasks.firmware_task import FirmwareDeployHistoryInfo
from local_console.core.deploy.tasks.model_task import ModelDeployHistoryInfo
from pydantic import BaseModel


class DeviceDeployHistoryInfo(BaseModel):
    device_id: str
    device_name: str


class DeployHistory(BaseModel):
    """
    `config_id`, `edge_system_sw_package`, `models` and `edge_apps` are ConfigTask-specific
    """

    deploy_id: str
    config_id: str | None = None
    from_datetime: datetime
    deploy_type: str
    deploying_cnt: int
    success_cnt: int
    fail_cnt: int
    edge_system_sw_package: list[FirmwareDeployHistoryInfo] | None = None
    models: list[ModelDeployHistoryInfo] | None = None
    edge_apps: list[AppDeployHistoryInfo] | None = None
    devices: list[DeviceDeployHistoryInfo] | None = None


class DeployHistoryList(BaseModel):
    deploy_history: list[DeployHistory]
    continuation_token: str | None = None
