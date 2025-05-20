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
from local_console.core.files.exceptions import FileNotFound
from local_console.core.files.files import FilesManager
from local_console.core.files.values import FileInfo
from local_console.core.files.values import FileType
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


# OpenAPI reflects 2 possible schemas:
# - InputFileIdOfImportBaseModelJsonBody, which uses file_id for identifying files.
# - InputFileUrlOfImportBaseModelJsonBody, which does not use file_id and instead uses SAS_URL.
# LC implements only the schema that requires file_id
class PostModelsIn(BaseModel):
    model_id: str = Field(max_length=100)
    model_file_id: str

    model_config = ConfigDict(protected_namespaces=())


class Model(BaseModel):
    file: FileInfo
    info: PostModelsIn


class ModelManager:
    def __init__(self, file_manager: FilesManager) -> None:
        self._models: dict[str, Model] = {}
        self._file_manager = file_manager

    def register(self, info: PostModelsIn) -> None:
        file = self._file_manager.get_file(FileType.MODEL, info.model_file_id)
        if file is None:
            raise FileNotFound(info.model_file_id)
        self._models[info.model_id] = Model(file=file, info=info)

    def get_by_id(self, model_id: str) -> Model | None:
        if model_id not in self._models:
            return None
        return self._models[model_id]

    def get_all(self) -> list[Model]:
        return [self._models[key] for key in sorted(self._models.keys())]
