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
from typing import Callable
from uuid import uuid4

from fastapi import Request
from fastapi import Response
from starlette.datastructures import URL
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


def get_relative_url(url: URL) -> str:
    return str(url.path + ("?" + url.query if url.query else ""))


class LogAllRequestMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        request_id = str(uuid4())[:8]
        relative_url = get_relative_url(request.url)
        logger.info(
            f"Start: {request.method} {relative_url} | Id: {request_id} | {request.base_url}"
        )

        try:
            response = await call_next(request)

            logger.info(
                f"Done: {request.method} {relative_url} | Id: {request_id} | Status: {response.status_code}"
            )
            return response
        except Exception as e:
            logger.info(
                f"Fail: {request.method} {relative_url} | Id: {request_id}", exc_info=e
            )
            raise e
