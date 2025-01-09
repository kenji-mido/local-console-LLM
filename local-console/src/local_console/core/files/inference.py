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
import logging
from pathlib import Path

from local_console.core.files.device import InferenceFileManager
from local_console.core.files.exceptions import FileNotFound
from pydantic import BaseModel
from pydantic import Field
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class InferenceDetail(BaseModel):
    t: str = Field(..., alias="T")
    o: str = Field(..., alias="O")

    class Config:
        extra = "allow"
        populate_by_name = True


class Inference(BaseModel):
    device_id: str = Field(..., alias="DeviceID")
    model_id: str = Field(..., alias="ModelID")
    image: bool = Field(..., alias="Image")
    inferences: list[InferenceDetail] = Field(..., alias="Inferences")

    class Config:
        extra = "allow"
        populate_by_name = True


class InferenceWithSource(BaseModel):
    path: Path
    inference: Inference


class InferenceManager:
    def __init__(self, files: InferenceFileManager) -> None:
        self.files = files

    def _inference_or_none(self, inference_path: Path) -> InferenceWithSource | None:
        try:
            inf = Inference.model_validate_json(inference_path.read_text())
            return InferenceWithSource(path=inference_path, inference=inf)
        except ValidationError as e:
            logger.error(f"Could not parse inference from {inference_path}", exc_info=e)
        except Exception as e:
            logger.error(f"Unknown error from {inference_path}", exc_info=e)
        return None

    def list(self, device_id: int) -> list[InferenceWithSource]:
        files = self.files.list_for(device_id)
        return [inf for f in files if (inf := self._inference_or_none(f))]

    def get(self, device_id: int, inference_id: str) -> InferenceWithSource:
        inferences = [
            inf for inf in self.list(device_id) if inf.path.name == inference_id
        ]
        if len(inferences) < 1:
            raise FileNotFound(
                filename=inference_id,
                message=f"Inference file '{inference_id}' not found",
            )
        elif len(inferences) > 1:
            raise AssertionError(
                f"Multiple inference files with id '{inference_id}' exist"
            )
        return inferences[0]
