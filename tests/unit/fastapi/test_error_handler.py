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
import json
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi import status
from local_console.core.error.base import LocalConsoleException
from local_console.core.error.code import ErrorCodes
from local_console.fastapi.error_handler import handle_business_error
from local_console.fastapi.error_handler import handle_exception
from local_console.fastapi.error_handler import handle_http
from local_console.fastapi.error_handler import LocalConsoleErrorHandler


def test_generic_error():
    expected_message = "An error occurred"
    error = Exception(expected_message)
    request = MagicMock()

    result = handle_exception(request, error)

    assert result.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    body = json.loads(result.body)
    assert body["result"] == "ERROR"
    assert body["message"] == expected_message
    assert body["code"] == "001001"


def test_http_error():
    expected_message = "I'm a tea pod"
    expected_status = status.HTTP_418_IM_A_TEAPOT
    error = HTTPException(status_code=expected_status, detail=expected_message)
    request = MagicMock()

    result = handle_http(request, error)

    assert result.status_code == expected_status
    body = json.loads(result.body)
    assert body["result"] == "ERROR"
    assert body["message"] == expected_message
    assert body["code"] == "001002"


def test_local_console_exception():
    expected_message = "Business want to say this to the user"
    error = LocalConsoleException(
        code=ErrorCodes.EXTERNAL_DEPLOYMENT_ALREADY_RUNNING, message=expected_message
    )
    request = MagicMock()

    result = handle_business_error(request, error)

    assert result.status_code == status.HTTP_409_CONFLICT
    body = json.loads(result.body)
    assert body["result"] == "ERROR"
    assert body["message"] == expected_message
    assert body["code"] == "110001"


@pytest.mark.parametrize(
    "code,status",
    [
        [ErrorCodes.INTERNAL_INVALID_ERROR_CODE, 500],
        [ErrorCodes.INTERNAL_INVALID_USER_CODE, 500],
        [ErrorCodes.EXTERNAL_DEPLOYMENT_ALREADY_RUNNING, 409],
        [ErrorCodes.EXTERNAL_ONE_DEVICE_NEEDED, 416],
        [ErrorCodes.EXTERNAL_DEVICE_NOT_FOUND, 404],
        [ErrorCodes.EXTERNAL_CONFIG_UNITSIZE, 422],
    ],
)
def test_business_status(code: ErrorCodes, status: int) -> None:
    manager = LocalConsoleErrorHandler()
    assert manager.http_status(code) == status


@pytest.mark.parametrize("code", ErrorCodes)
def test_business_status_internal_or_external(code: ErrorCodes) -> None:
    manager = LocalConsoleErrorHandler()
    if code.is_internal():
        assert manager.http_status(code) >= 500
    else:
        assert manager.http_status(code) >= 400 and manager.http_status(code) < 500
