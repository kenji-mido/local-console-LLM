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
from enum import IntEnum

from local_console.core.camera.v2.components.req_res_info import ResInfo
from pydantic import BaseModel


class Flip(IntEnum):
    NORMAL = 0
    FLIP = 1


class DirectGetImageParameters(BaseModel):
    crop_h_offset: int = 0
    crop_v_offset: int = 0
    crop_h_size: int = 4056
    crop_v_size: int = 3040
    network_id: str = "999999"
    sensor_name: str = "sensor_chip"
    flip_horizontal: Flip = Flip.NORMAL
    flip_vertical: Flip = Flip.NORMAL


class ResInfoMaybeID(ResInfo):
    """
    Despite `direct_get_image` being a v2 command request, in T3P firmware v1.1.0
    it turns out that the reply to the request might be missing its `res_id` field.
    """

    res_id: str = ""


class DirectGetImageResponse(BaseModel):
    res_info: ResInfoMaybeID
    image: str
