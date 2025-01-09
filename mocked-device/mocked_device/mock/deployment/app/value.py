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
from pydantic import HttpUrl
from pydantic.alias_generators import to_camel


class SnakeModel(BaseModel):
    class Config:
        alias_generator = to_camel


class ModuleSpec(SnakeModel):
    download_url: HttpUrl


class DeploymentConfig(SnakeModel):
    deployment_id: str
    modules: dict[str, ModuleSpec]
