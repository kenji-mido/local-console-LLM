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
from pydantic import BaseModel


class Module(BaseModel):
    entryPoint: str
    moduleImpl: str
    downloadUrl: str
    hash: str


class InstanceSpec(BaseModel):
    moduleId: str
    subscribe: dict
    publish: dict


class DeploymentConfigV2(BaseModel):
    deploymentId: str
    instanceSpecs: dict[str, InstanceSpec]
    modules: dict[str, Module]
    publishTopics: dict
    subscribeTopics: dict
