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
from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from local_console.core.models import Model
from local_console.core.models import ModelManager
from local_console.core.models import PostModelsIn
from local_console.fastapi.dependencies.deploy import InjectModelManager
from local_console.fastapi.pagination import Paginator
from local_console.fastapi.routes.commons import EmptySuccess
from pydantic import BaseModel

router = APIRouter(prefix="/models", tags=["Model"])


class ModelDTO(BaseModel):
    model_id: str


class GetModelsOutDTO(BaseModel):
    models: list[ModelDTO]
    continuation_token: str | None = None


class ModelsPaginator(Paginator):
    @classmethod
    def _get_element_key(cls, element: Model) -> str:
        return element.info.model_id


class ModuleController:
    def __init__(
        self,
        model_manager: ModelManager,
        paginator: ModelsPaginator = ModelsPaginator(),
    ):
        self.model_manager = model_manager
        self.paginator = paginator

    def _to_model(self, model: Model) -> ModelDTO:
        return ModelDTO(
            model_id=model.info.model_id,
        )

    def register(self, request: PostModelsIn) -> EmptySuccess:
        self.model_manager.register(request)
        return EmptySuccess()

    def list(self, limit: int, starting_after: str | None) -> GetModelsOutDTO:
        all: list[Model] = self.model_manager.get_all()
        paginated, continuation = self.paginator.paginate(all, limit, starting_after)
        model_list = [self._to_model(m) for m in paginated]
        return GetModelsOutDTO(models=model_list, continuation_token=continuation)


def module_controller(model_manager: InjectModelManager) -> ModuleController:
    return ModuleController(model_manager=model_manager)


InjectModuleController = Annotated[ModuleController, Depends(module_controller)]


# OpenAPI 'ImportBaseModel'
@router.post("")
def post_models(
    request: PostModelsIn, controller: InjectModuleController
) -> EmptySuccess:
    return controller.register(request)


# OpenAPI 'GetModels'
@router.get("")
def get_models(
    controller: InjectModuleController,
    limit: int = Query(
        50, ge=0, le=256, description="Number of Models to fetch. Value range: 0 to 256"
    ),
    starting_after: str | None = Query(
        None, description="A token to use in pagination."
    ),
) -> GetModelsOutDTO:
    return controller.list(limit, starting_after)
