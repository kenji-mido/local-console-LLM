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
from enum import Enum
from enum import IntEnum
from typing import Any

from pydantic import BaseModel

# The classes below are copied from:
#  local_console/core/camera/v2/components/edge_app.py
#  local_console/core/camera/v2/components/req_res_info.py


class ReqInfo(BaseModel):
    req_id: str


class ResponseCode(IntEnum):
    OK = 0
    CANCELLED = 1
    UNKNOWN = 2
    INVALID_ARGUMENT = 3
    DEADLINE_EXCEEDED = 4
    NOT_FOUND = 5
    ALREADY_EXISTS = 6
    PERMISSION_DENIED = 7
    RESOURCE_EXHAUSTED = 8
    FAILED_PRECONDITION = 9
    ABORTED = 10
    OUT_OF_RANGE = 11
    UNIMPLEMENTED = 12
    INTERNAL = 13
    UNAVAILABLE = 14
    DATA_LOSS = 15
    UNAUTHENTICATED = 16


class ResInfo(BaseModel):
    res_id: str
    code: ResponseCode
    detail_msg: str


class ProcessState(Enum):
    STOPPED = 1
    RUNNING = 2


class UploadMethod(Enum):
    MQTT_TELEMETRY = 0
    BLOB_STORAGE = 1
    HTTP_STORAGE = 2


class CodecSettingsSpec(BaseModel):
    format: int | None = None


class CameraImageSizeSpec(BaseModel):
    width: int | None = None
    height: int | None = None
    scaling_policy: int | None = None


class ManualWhiteBalanceGainSpec(BaseModel):
    red: int | float | None = None
    blue: int | float | None = None


class CameraImageFlipSpec(BaseModel):
    flip_vertical: int | None = None
    flip_horizontal: int | None = None


class FrameRateSpec(BaseModel):
    num: int | None = None
    denom: int | None = None


class AutoExposureSpec(BaseModel):
    max_gain: int | float | None = None
    convergence_speed: int | float | None = None
    max_exposure_time: int | float | None = None
    min_exposure_time: int | float | None = None


class AutoWhiteBalanceSpec(BaseModel):
    convergence_speed: int | float | None = None


class ManualExposureSpec(BaseModel):
    gain: int | float | None = None
    exposure_time: int | float | None = None


class ImageCroppingSpec(BaseModel):
    top: int | None = None
    left: int | None = None
    width: int | None = None
    height: int | None = None


class ManualWhiteBalancePresetSpec(BaseModel):
    color_temperature: int | float | None = None


class PQSettings(BaseModel):
    frame_rate: FrameRateSpec | None = None
    digital_zoom: int | float | None = None
    auto_exposure: AutoExposureSpec | None = None
    exposure_mode: int | float | None = None
    image_cropping: ImageCroppingSpec | None = None
    image_rotation: int | float | None = None
    ev_compensation: int | float | None = None
    manual_exposure: ManualExposureSpec | None = None
    camera_image_flip: CameraImageFlipSpec | None = None
    camera_image_size: CameraImageSizeSpec | None = None
    auto_white_balance: AutoWhiteBalanceSpec | None = None
    white_balance_mode: int | float | None = None
    ae_anti_flicker_mode: int | float | None = None
    manual_white_balance_gain: ManualWhiteBalanceGainSpec | None = None
    manual_white_balance_preset: ManualWhiteBalancePresetSpec | None = None


class UploadSpec(BaseModel):
    enabled: bool = False
    method: UploadMethod | None = None
    endpoint: str | None = None
    path: str | None = None
    storage_name: str | None = None


class EdgeAppPortSettings(BaseModel):
    metadata: UploadSpec | None = None
    input_tensor: UploadSpec | None = None


class InferenceSettingsSpec(BaseModel):
    number_of_iterations: int | None = None


class EdgeAppCommonSettings(BaseModel):
    log_level: int | None = None
    port_settings: EdgeAppPortSettings | None = None
    pq_settings: PQSettings | None = None
    process_state: ProcessState | None = None
    codec_settings: CodecSettingsSpec | None = None
    upload_interval: int | None = None
    inference_settings: InferenceSettingsSpec | None = None
    number_of_inference_per_message: int | None = None


class EdgeAppSpec(BaseModel):
    req_info: ReqInfo | None = None
    res_info: ResInfo | None = None
    common_settings: EdgeAppCommonSettings | None = None
    custom_settings: Any | None = None


APP_CONFIG_KEY = "edge_app"
