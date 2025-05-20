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
from mocked_device.device import AppStates
from mocked_device.utils.fake import fake_image
from mocked_device.utils.json import json_bytes
from mocked_device.utils.request import upload
from mocked_device.utils.timing import as_timestamp
from pydantic import BaseModel
from pydantic import Field


class UploadingParams(BaseModel):
    uploadMode: int = Field(alias="Mode")
    images_url: str = Field(alias="StorageName")
    images_path: str = Field(alias="StorageSubDirectoryPath")
    inference_url: str = Field(alias="StorageNameIR")
    inference_path: str = Field(alias="StorageSubDirectoryPathIR")
    interval: int = Field(alias="UploadInterval")


def get_inference(
    app_type: AppStates, is_app_deployed: bool, is_model_deployed: bool
) -> str:
    if is_app_deployed and is_model_deployed:
        if app_type == AppStates.ZoneDetection:
            return "DAAAAAAABgAKAAQABgAAAAwAAAAAAAYACAAEAAYAAAAEAAAAAQAAABQAAAAQABQAAAAGAAgADAAQAAcAEAAAAAAAAQEYAAAAEQCsPh+Faz4MABQABAAIAAwAEAAMAAAABwEAAHkAAAAsAQAArwAAAA=="
        if app_type == AppStates.Detection:
            return "DAAAAAAABgAKAAQABgAAAAwAAAAAAAYACAAEAAYAAAAEAAAAAQAAABAAAAAMABAAAAAHAAgADAAMAAAAAAAAARQAAAAAAKw+DAAUAAQACAAMABAADAAAAAcBAAB5AAAALAEAAK8AAAA="
        if app_type == AppStates.Classification:
            return "DAAAAAAABgAKAAQABgAAAAwAAAAAAAYACAAEAAYAAAAEAAAABQAAAFAAAAA4AAAAKAAAABwAAAAEAAAAzP///wIAAAAAAKA9CAAIAAAABAAIAAAAAAAsPuj///8EAAAAAABAPvT///8BAAAAAABcPggADAAEAAgACAAAAAMAAAAAALQ+"
        raise NotImplementedError("Unknown app type")
    if not is_app_deployed and not is_model_deployed:
        return "AABAvQAAQD0AAKA9AACAPAAAQD0AAEC9AAAAvgAAwD0AAAA9AADAvQ=="
    raise NotImplementedError


def upload_fake_image(params: UploadingParams, timestamp: str | None = None) -> None:
    if not timestamp:
        timestamp = as_timestamp()
    file_name = f"{timestamp}.jpg"
    url = f"{params.images_url}/{params.images_path}/{file_name}"
    headers = {
        "Content-Type": "image/jpg",
        "Content-Disposition": f'attachment; filename="{file_name}"',
    }
    upload(url, fake_image(), headers)


def upload_fake_inference(
    params: UploadingParams,
    app_type: AppStates,
    is_app_deployed: bool,
    is_model_deployed: bool,
    timestamp: str | None = None,
) -> None:
    if not timestamp:
        timestamp = as_timestamp()
    file_name = f"{timestamp}.txt"
    url = f"{params.inference_url}/{params.inference_path}/{file_name}"
    inference = {
        "DeviceID": "sid-100A50500A2010072664012000000000",
        "ModelID": "0308000000000100",
        "Image": True,
        "Inferences": [
            {
                "T": f"{timestamp}",
                "O": get_inference(app_type, is_app_deployed, is_model_deployed),
                "unexpected_field": "with value",
            }
        ],
        "additional_field": "some value",
    }
    headers = {
        "Content-Type": "text/plain",
        "Content-Disposition": f'attachment; filename="{file_name}"',
    }
    upload(url, json_bytes(inference), headers)
