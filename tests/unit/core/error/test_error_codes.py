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
from local_console.core.error.code import ErrorCodes


def test_no_duplicate_codes():
    codes = [error.value for error in ErrorCodes]
    assert len(codes) == len(set(codes))
    assert len(codes) == len(ErrorCodes.__members__.values())


def test_codes_are_numeric():
    for error in ErrorCodes:
        assert error.value.isdigit()
        assert len(error.value) == 6


def test_check_internal():
    assert not ErrorCodes.EXTERNAL_DEPLOYMENT_ALREADY_RUNNING.is_internal()
