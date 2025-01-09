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
from local_console.fastapi.routes.deploy_history.dependencies import (
    InjectDeployHistoryController,
)
from local_console.fastapi.routes.deploy_history.dto import DeployHistoryList


router = APIRouter(prefix="/deploy_history", tags=["Config"])


@router.get("")
async def list(
    controller: InjectDeployHistoryController,
    limit: int = Query(
        50,
        ge=0,
        le=256,
        description="Number of the items to fetch information",
    ),
    starting_after: str | None = Query(
        None,
        description="Retrieves additional data beyond the number of targets specified by the query parameter (limit). Specify the value obtained from the response (continuation_token) to fetch the next data.",
    ),
) -> DeployHistoryList:
    return controller.get_list(limit, starting_after)
