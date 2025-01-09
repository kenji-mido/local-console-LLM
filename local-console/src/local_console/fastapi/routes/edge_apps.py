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
from fastapi import APIRouter
from fastapi import Query
from local_console.core.edge_apps import EdgeApp
from local_console.core.edge_apps import PostEdgeAppsRequestIn
from local_console.fastapi.dependencies.deploy import InjectEdgeAppsManager
from local_console.fastapi.pagination import EdgeAppsPaginator
from pydantic import BaseModel

router = APIRouter(prefix="/edge_apps", tags=["Edge App"])


class EdgeAppVersion(BaseModel):
    app_version: str
    root_dtmi: None | str = None
    compiled_flg: None | str = None
    status: None | str = None
    description: None | str = None
    deploy_count: None | str = None
    ins_id: None | str = None
    ins_date: None | str = None
    upd_id: None | str = None
    upd_date: None | str = None


class EdgeAppInfoDTO(BaseModel):
    app_name: str
    versions: list[EdgeAppVersion]


class GetEdgeAppsRequestOutDTO(BaseModel):
    continuation_token: str | None = None
    apps: list[EdgeAppInfoDTO]


class PostEdgeAppRequestOutDTO(BaseModel):
    result: str = "SUCCESS"


@router.get("")
async def get_edge_apps(
    edge_app_manager: InjectEdgeAppsManager,
    limit: int = Query(
        50,
        ge=0,
        le=256,
        description="Number of Edge Apps to fetch. Value range: 0 to 256",
    ),
    starting_after: str | None = Query(
        None, description="A token to use in pagination."
    ),
) -> GetEdgeAppsRequestOutDTO:
    list_all_edge_apps: list[EdgeApp] = edge_app_manager.get_all_edge_apps()

    list_filtered_edge_apps, continuation_token = EdgeAppsPaginator().paginate(
        list_all_edge_apps, limit=limit, continuation_token=starting_after
    )

    list_filtered_edge_apps_dto = [
        EdgeAppInfoDTO(
            app_name=edge_app.info.app_name,
            versions=[],
        )
        for edge_app in list_filtered_edge_apps
    ]

    return GetEdgeAppsRequestOutDTO(
        continuation_token=continuation_token, apps=list_filtered_edge_apps_dto
    )


@router.post("")
async def post_edge_apps(
    request: PostEdgeAppsRequestIn, edge_app_manager: InjectEdgeAppsManager
) -> PostEdgeAppRequestOutDTO:
    edge_app_manager.register(request)
    return PostEdgeAppRequestOutDTO()
