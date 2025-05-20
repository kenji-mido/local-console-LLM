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
from mocked_device.mock_v2.message import SystemInfo
from mocked_device.mock_v2.message import SystemInfoV2


class SystemInfoRPIModel(SystemInfo):
    os: str = "Linux"
    arch: str = "aarch64"
    evp_agent: str = "v1.40.0"
    evp_agent_commit_hash: str = "19ba152d5ad174999ac3a0e669eece54b312e5d1"
    wasmMicroRuntime: str = "v2.1.0"
    protocolVersion: str = "EVP2-TB"


class SystemInfoRPI(SystemInfoV2):
    systemInfo: SystemInfoRPIModel = SystemInfoRPIModel()
