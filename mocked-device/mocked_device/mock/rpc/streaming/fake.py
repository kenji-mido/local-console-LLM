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
from datetime import datetime

from mocked_device.mock.rpc.fake import fake_image
from mocked_device.mock.rpc.streaming.values import UploadingParams
from mocked_device.utils.json import json_bytes
from mocked_device.utils.request import upload


def now_str() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]


def upload_fake_image(params: UploadingParams, timestamp: str | None = None) -> None:
    if not timestamp:
        timestamp = now_str()
    file_name = f"{timestamp}.jpg"
    url = f"{params.images_url}/{params.images_path}/{file_name}"
    headers = {
        "Content-Type": "image/jpg",
        "Content-Disposition": f'attachment; filename="{file_name}"',
    }
    upload(url, fake_image(), headers)


def upload_fake_inference(
    params: UploadingParams, timestamp: str | None = None
) -> None:
    if not timestamp:
        timestamp = now_str()
    file_name = f"{timestamp}.txt"
    url = f"{params.inference_url}/{params.inference_path}/{file_name}"
    inference = {
        "DeviceID": "sid-100A50500A2010072664012000000000",
        "ModelID": "0308000000000100",
        "Image": True,
        "Inferences": [
            {
                "T": f"{timestamp}",
                "O": "DAAAAAAABgAKAAQABgAAAAwAAAAAAAYACAAEAAYAAAAEAAAABQAAAFAAAAA4AAAAKAAAABwAAAAEAAAAzP///wIAAAAAAKA9CAAIAAAABAAIAAAAAAAsPuj///8EAAAAAABAPvT///8BAAAAAABcPggADAAEAAgACAAAAAMAAAAAALQ+",
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
