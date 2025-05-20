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
from local_console.core.files.inference import InferenceOut
from local_console.fastapi.routes.images.dto import FileDTO
from pydantic import BaseModel
from pydantic import ConfigDict


class InferenceElementDTO(BaseModel):
    id: str
    model_id: str
    model_version_id: str = ""
    inference_result: InferenceOut

    model_config = ConfigDict(protected_namespaces=())


class InferenceListDTO(BaseModel):
    data: list[InferenceElementDTO]
    continuation_token: str | None


class InferenceImagePairDTO(BaseModel):
    id: str
    inference: InferenceElementDTO
    image: FileDTO


class InferenceWithImageListDTO(BaseModel):
    data: list[InferenceImagePairDTO]
    continuation_token: str | None
