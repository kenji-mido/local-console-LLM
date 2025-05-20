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
from typing import Any

from mocked_device.device import AppStates
from mocked_device.mock_v2.ea_config import EdgeAppCommonSettings
from mocked_device.utils.fake import fake_image
from mocked_device.utils.json import json_bytes
from mocked_device.utils.request import upload
from mocked_device.utils.timing import as_timestamp
from mocked_device.utils.timing import now


def get_inference(
    app_type: AppStates, is_app_deployed: bool, is_model_deployed: bool
) -> list[dict[str, Any]]:

    if not is_app_deployed and not is_model_deployed:
        return []

    if is_app_deployed and is_model_deployed:
        if app_type == AppStates.Detection:
            return [
                {
                    "class_id": 0,
                    "score": 0.92578125,
                    "bounding_box": {
                        "left": 148,
                        "top": 140,
                        "right": 264,
                        "bottom": 212,
                    },
                },
                {
                    "class_id": 1,
                    "score": 0.89234252,
                    "bounding_box": {
                        "left": 37,
                        "top": 39,
                        "right": 153,
                        "bottom": 101,
                    },
                },
            ]

        if app_type == AppStates.Classification:
            return [
                {
                    "class_id": 88,
                    "score": 0.9111,
                    "bounding_box": {
                        "left": 100,
                        "top": 100,
                        "right": 150,
                        "bottom": 150,
                    },
                },
                {
                    "class_id": 77,
                    "score": 0.9222,
                    "bounding_box": {"left": 20, "top": 20, "right": 90, "bottom": 90},
                },
            ]

        raise NotImplementedError("Unknown app type")

    raise NotImplementedError


def upload_fake_image(
    params: EdgeAppCommonSettings, timestamp: str | None = None
) -> None:
    assert params.port_settings and params.port_settings.input_tensor
    if not timestamp:
        timestamp = as_timestamp(now())
    file_name = f"{timestamp}.jpg"
    ps = params.port_settings.input_tensor

    assert ps.endpoint and ps.path
    url = f"{ps.endpoint}/{ps.path}/{file_name}"
    headers = {
        "Content-Type": "image/jpg",
        "Content-Disposition": f'attachment; filename="{file_name}"',
    }
    upload(url, fake_image(), headers)


def upload_fake_inference(
    params: EdgeAppCommonSettings,
    app_type: AppStates,
    is_app_deployed: bool,
    is_model_deployed: bool,
    timestamp: str | None = None,
) -> None:
    assert params.port_settings and params.port_settings.metadata

    if not timestamp:
        timestamp = as_timestamp(now())
    file_name = f"{timestamp}.txt"
    ps = params.port_settings.metadata

    assert ps.endpoint and ps.path
    url = f"{ps.endpoint}/{ps.path}/{file_name}"

    inference = {
        "DeviceID": "sid-100A50500A2010072664012000000000",
        "ModelID": "0308000000000100",
        "Image": True,
        "Inferences": [
            {
                "T": f"{timestamp}",
                "O": get_inference(app_type, is_app_deployed, is_model_deployed),
                "F": "1",
            }
        ],
        "additional_field": "some value",
    }
    headers = {
        "Content-Type": "text/plain",
        "Content-Disposition": f'attachment; filename="{file_name}"',
    }
    upload(url, json_bytes(inference), headers)
