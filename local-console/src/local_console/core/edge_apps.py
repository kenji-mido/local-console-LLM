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


class PostEdgeAppsRequestIn(BaseModel):
    description: str | None = None
    app_name: str
    app_version: str | None = None
    edge_app_package_id: str


class EdgeApp(BaseModel):
    info: PostEdgeAppsRequestIn
    file: FileInfo


class EdgeAppsManager:
    def __init__(self, file_manager: FilesManager) -> None:
        self._edge_apps: dict[str, EdgeApp] = dict()
        self._file_manager = file_manager

    def register(self, edge_app_info: PostEdgeAppsRequestIn) -> None:
        file = self._file_manager.get_file(
            file_type=FileType.APP, file_id=edge_app_info.edge_app_package_id
        )
        if file is None:
            raise FileNotFound(edge_app_info.edge_app_package_id)
        self._edge_apps[edge_app_info.edge_app_package_id] = EdgeApp(
            info=edge_app_info, file=file
        )

    def get_all_edge_apps(self) -> list[EdgeApp]:
        return list(self._edge_apps.values())

    def get_by_id(self, edge_app_id: str) -> None | EdgeApp:
        if edge_app_id not in self._edge_apps:
            return None
        return self._edge_apps[edge_app_id]
