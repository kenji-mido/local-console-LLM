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
import pytest
from local_console.core.error.base import InternalException
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes


def test_user_error_needs_user_codes() -> None:
    with pytest.raises(InternalException) as error:
        UserException(code=ErrorCodes.INTERNAL_INVALID_ERROR_CODE, message="")

    assert (
        str(error.value)
        == f"Error code {ErrorCodes.INTERNAL_INVALID_ERROR_CODE} is not external error."
    )
    assert error.value.code == ErrorCodes.INTERNAL_INVALID_USER_CODE


def test_internal_error_needs_internal_codes() -> None:
    with pytest.raises(InternalException) as error:
        InternalException(
            code=ErrorCodes.EXTERNAL_DEPLOYMENT_ALREADY_RUNNING, message=""
        )

    assert (
        str(error.value)
        == f"Error code {ErrorCodes.EXTERNAL_DEPLOYMENT_ALREADY_RUNNING} is not internal error."
    )
    assert error.value.code == ErrorCodes.INTERNAL_INVALID_ERROR_CODE
