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
from typing import Any

import requests


logger = logging.getLogger(__name__)


def download(url: str) -> bytes:
    try:
        response = requests.get(url)

        logger.info(f"downloading {url} {response.status_code}")

        if response.status_code >= 400:
            logger.error(f"Could not download {response.status_code}")
            logger.error(f"details {response.text}")
            return b""
        return response.content
    except BaseException as e:
        logger.error(f"Could not download from {url}", exc_info=e)
        return b""


def upload(url: str, content: bytes, headers: dict[str, Any]) -> None:
    try:
        response = requests.post(url, data=content, headers=headers)

        logger.info(f"uploading {url} {response.status_code}")

        if response.status_code >= 400:
            logger.error(f"Could not upload {response.status_code}")
            logger.error(f"details {response.text}")
    except BaseException as e:
        logger.error(f"Could not download from {url}", exc_info=e)
        return None
