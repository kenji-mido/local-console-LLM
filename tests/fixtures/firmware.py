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
from contextlib import contextmanager
from unittest.mock import patch

from local_console.core.camera.enums import OTAUpdateStatus


def generate_get_ota_update_status_mock(sequence: list[OTAUpdateStatus]):
    index = 0

    def func(state):
        nonlocal index  # reference the outer "index" variable.
        if index < len(sequence):
            val = sequence[index]
            index += 1
            return val
        # fallback to the last status.
        return sequence[-1]

    return func


@contextmanager
def mock_get_ota_update_status(filepath: str, sequence: list[OTAUpdateStatus]):
    with patch(
        filepath,
        generate_get_ota_update_status_mock(sequence),
    ):
        yield
