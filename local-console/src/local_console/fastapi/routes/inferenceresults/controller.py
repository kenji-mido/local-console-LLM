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
from local_console.core.files.inference import Inference
from local_console.core.files.inference import InferenceManager
from local_console.core.files.inference import InferenceWithSource
from local_console.fastapi.pagination import Paginator
from local_console.fastapi.routes.inferenceresults.dto import InferenceElementDTO
from local_console.fastapi.routes.inferenceresults.dto import InferenceListDTO


def id(inf: InferenceWithSource) -> str:
    return inf.path.name


class InferencePaginator(Paginator):
    @classmethod
    def _get_element_key(cls, element: InferenceWithSource) -> str:
        return id(element)


class InferencesController:
    def __init__(
        self, manager: InferenceManager, paginator: InferencePaginator | None = None
    ) -> None:
        self.manager = manager
        self.paginator = paginator or InferencePaginator()

    def _to_dto(self, inf: InferenceWithSource) -> InferenceElementDTO:
        return InferenceElementDTO(
            id=id(inf), model_id=inf.inference.model_id, inference_result=inf.inference
        )

    def list(
        self, device_id: int, limit: int, starting_after: str | None
    ) -> InferenceListDTO:
        paths = self.manager.list(device_id)
        trimmed, continuation = self.paginator.paginate(paths, limit, starting_after)
        return InferenceListDTO(
            data=[self._to_dto(inference) for inference in trimmed],
            continuation_token=continuation,
        )

    def get(self, device_id: int, inference_id: str) -> Inference:
        return self.manager.get(device_id, inference_id).inference
