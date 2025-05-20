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

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi import status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from local_console.core.error.base import LocalConsoleException
from local_console.core.error.code import DEPLOYMENT
from local_console.core.error.code import ErrorCodes
from local_console.core.files.exceptions import FileNotFound
from pydantic import BaseModel
from pydantic import field_validator

logger = logging.getLogger(__name__)


class ErrorDetails(BaseModel):
    result: str = "ERROR"
    message: str
    code: str | ErrorCodes

    @field_validator("code")
    @classmethod
    def has_right_format(cls, v: str | ErrorCodes) -> str:
        if isinstance(v, ErrorCodes):
            return v.value
        return v


def handle_http(request: Request, error: HTTPException) -> JSONResponse:
    logger.info("Unexpected generic error", exc_info=error)
    return JSONResponse(
        content=ErrorDetails(
            message=error.detail, code=ErrorCodes.INTERNAL_HTTP
        ).model_dump(),
        status_code=error.status_code,
    )


class LocalConsoleErrorHandler:

    def _user_status(self, code: ErrorCodes) -> Any:
        if code.is_subtype(DEPLOYMENT):
            return status.HTTP_409_CONFLICT
        if code == ErrorCodes.EXTERNAL_ONE_DEVICE_NEEDED:
            return status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE
        if code == ErrorCodes.EXTERNAL_DEVICE_NOT_FOUND:
            return status.HTTP_404_NOT_FOUND
        if code == ErrorCodes.EXTERNAL_CONFIG_UNITSIZE:
            return status.HTTP_422_UNPROCESSABLE_ENTITY
        return status.HTTP_400_BAD_REQUEST

    def _internal_status(self) -> Any:
        return status.HTTP_500_INTERNAL_SERVER_ERROR

    def http_status(self, code: ErrorCodes) -> Any:
        if code.is_internal():
            return self._internal_status()
        return self._user_status(code)

    def handle(self, error: LocalConsoleException) -> JSONResponse:
        code = error.code
        return JSONResponse(
            content=ErrorDetails(message=str(error), code=code).model_dump(),
            status_code=self.http_status(code),
        )


def handle_business_error(
    request: Request, error: LocalConsoleException
) -> JSONResponse:
    logger.info("Business error", exc_info=error)
    manager = LocalConsoleErrorHandler()
    return manager.handle(error)


def handle_pydantic_validation(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    logger.info("Validation error", exc_info=error)

    def format_error(error: dict[str, Any]) -> str:
        loc, msg = error["loc"], error["msg"]
        filtered_loc = loc[1:] if loc[0] in ("body", "query", "path") else loc
        if len(filtered_loc) > 3:
            filtered_loc = filtered_loc[-3:]
        field_string = ".".join([str(non_str) for non_str in filtered_loc])
        return f"{field_string}: {msg}"

    msg = " and ".join(format_error(e) for e in error.errors())
    return JSONResponse(
        content=ErrorDetails(
            message=msg, code=ErrorCodes.INTERNAL_PYDANTIC
        ).model_dump(),
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


def handle_exception(request: Request, error: Exception) -> JSONResponse:
    logger.info("Unexpected generic error", exc_info=error)
    return JSONResponse(
        content=ErrorDetails(
            message=str(error), code=ErrorCodes.INTERNAL_GENERIC
        ).model_dump(),
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def handle_file_exception(request: Request, error: FileNotFound) -> JSONResponse:
    logger.info("File error", exc_info=error)
    message = (
        str(error)
        if error.args and error.args[0]
        else f"Could not find file {error.filename}"
    )
    return JSONResponse(
        content=ErrorDetails(
            message=message, code=ErrorCodes.EXTERNAL_NOTFOUND
        ).model_dump(),
        status_code=status.HTTP_404_NOT_FOUND,
    )


def handle_all_exceptions(app: FastAPI) -> None:
    app.add_exception_handler(LocalConsoleException, handle_business_error)
    app.add_exception_handler(FileNotFound, handle_file_exception)
    app.add_exception_handler(RequestValidationError, handle_pydantic_validation)
    app.add_exception_handler(HTTPException, handle_http)
    app.add_exception_handler(Exception, handle_exception)
