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
from local_console.core.files.inference import InferenceDetail
from local_console.core.files.inference import InferenceDetailOut
from local_console.core.files.inference import InferenceManager
from local_console.core.files.inference import InferenceOut
from local_console.core.files.inference import InferenceType
from local_console.core.files.inference import InferenceWithSource
from local_console.core.schemas.schemas import DeviceID
from local_console.fastapi.pagination import Paginator
from local_console.fastapi.routes.images.controller import ImagesController
from local_console.fastapi.routes.inferenceresults.dto import InferenceElementDTO
from local_console.fastapi.routes.inferenceresults.dto import InferenceImagePairDTO
from local_console.fastapi.routes.inferenceresults.dto import InferenceListDTO
from local_console.fastapi.routes.inferenceresults.dto import InferenceWithImageListDTO


def id(inf: InferenceWithSource) -> str:
    return inf.path.name


class InferencePaginator(Paginator):
    @classmethod
    def _get_element_key(cls, element: InferenceWithSource) -> str:
        return id(element)


class InferenceImagePairPaginator(Paginator):
    @classmethod
    def _get_element_key(cls, element: InferenceImagePairDTO) -> str:
        return element.id


class InferencesController:
    def __init__(
        self, manager: InferenceManager, paginator: InferencePaginator | None = None
    ) -> None:
        self.manager = manager
        self.paginator = paginator or InferencePaginator()

    def _to_inf_det_out(
        self, infs_det: list[InferenceDetail]
    ) -> list[InferenceDetailOut]:
        return [
            InferenceDetailOut(
                time=inf_det.t,
                data=inf_det.o,
                ftype=inf_det.f or InferenceType.FLATBUFFER,
            )
            for inf_det in infs_det
        ]

    def _to_inf_out(self, inf: Inference) -> InferenceOut:
        return InferenceOut(
            device_id=inf.device_id,
            model_id=inf.model_id,
            image=inf.image,
            inferences=self._to_inf_det_out(inf.inferences),
        )

    def _to_dto(self, inf: InferenceWithSource) -> InferenceElementDTO:
        return InferenceElementDTO(
            id=id(inf),
            model_id=inf.inference.model_id,
            inference_result=self._to_inf_out(inf.inference),
        )

    def list(
        self, device_id: DeviceID, limit: int, starting_after: str | None
    ) -> InferenceListDTO:
        paths = self.manager.list(device_id)
        trimmed, continuation = self.paginator.paginate(paths, limit, starting_after)
        return InferenceListDTO(
            data=[self._to_dto(inference) for inference in trimmed],
            continuation_token=continuation,
        )

    def list_with_images(
        self,
        device_id: DeviceID,
        img_controller: ImagesController,
        limit: int,
        starting_after: str | None,
    ) -> InferenceWithImageListDTO:
        paths_ifc = self.manager.list(device_id)
        paths_img = img_controller.image_manager.list_for(device_id)

        in_inferences = {ifc.path.stem: ifc for ifc in paths_ifc}
        in_images = {img.stem: img for img in paths_img}

        ts_in_images = set(in_images.keys())
        ts_in_inferences = set(in_inferences.keys())
        paired_ids = ts_in_images & ts_in_inferences

        pairs = [
            InferenceImagePairDTO(
                id=pid,
                image=img_controller._to_file_dto(in_images[pid], device_id),
                inference=self._to_dto(in_inferences[pid]),
            )
            for pid in sorted(paired_ids, reverse=True)
        ]

        paginator = InferenceImagePairPaginator()
        trimmed, token = paginator.paginate(pairs, limit, starting_after)
        return InferenceWithImageListDTO(
            data=trimmed,
            continuation_token=token,
        )

    def get(self, device_id: DeviceID, inference_id: str) -> InferenceOut:
        return self._to_inf_out(self.manager.get(device_id, inference_id).inference)
