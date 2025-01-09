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
from enum import Enum


INTERNAL = "0"
EXTERNAL = "1"

GENERIC = "01"
ERROR = "02"
DEPLOYMENT = "10"
FIRMWARE = "11"
DEVICE = "20"


def code(source: str, type: str, detail: str) -> str:
    code = f"{source}{type}{detail}"
    assert int(code)
    return code


def internal(type: str, detail: str) -> str:
    return code(INTERNAL, type, detail)


def external(type: str, detail: str) -> str:
    return code(EXTERNAL, type, detail)


class ErrorCodes(Enum):
    INTERNAL_GENERIC = internal(GENERIC, "001")
    INTERNAL_HTTP = internal(GENERIC, "002")
    INTERNAL_PYDANTIC = internal(GENERIC, "003")
    INTERNAL_DEVICE_RPC_MISSING_CLIENT = internal(DEVICE, "001")
    INTERNAL_INVALID_ERROR_CODE = internal(ERROR, "001")
    INTERNAL_INVALID_USER_CODE = internal(ERROR, "002")
    EXTERNAL_NOTFOUND = external(GENERIC, "001")
    EXTERNAL_DEPLOYMENT_ALREADY_RUNNING = external(DEPLOYMENT, "001")
    EXTERNAL_FIRMWARE_VERSION_6_CHARS = external(FIRMWARE, "001")
    EXTERNAL_FIRMWARE_VERSION_8_CHARS = external(FIRMWARE, "002")
    EXTERNAL_FIRMWARE_SAME_VERSION = external(FIRMWARE, "003")
    EXTERNAL_ONE_DEVICE_NEEDED = external(DEVICE, "001")
    EXTERNAL_DEVICE_NAMES_MUST_BE_UNIQUE = external(DEVICE, "002")
    EXTERNAL_DEVICE_PORTS_MUST_BE_UNIQUE = external(DEVICE, "003")
    EXTERNAL_DEVICE_PORTS_MUST_BE_IN_TCP_RANGE = external(DEVICE, "004")
    EXTERNAL_DEVICE_CREATION_VALIDATION = external(DEVICE, "005")
    EXTERNAL_DEVICE_PORT_ALREADY_IN_USE = external(DEVICE, "006")
    EXTERNAL_DEVICE_NOT_FOUND = external(DEVICE, "007")
    EXTERNAL_EMPTY_FILE = external(GENERIC, "004")
    EXTERNAL_FILE_ALREADY_EXISTS = external(GENERIC, "005")
    EXTERNAL_CANNOT_USE_DIRECTORY = external(GENERIC, "006")
    EXTERNAL_FIRMWARE_INVALID_APP_FILE = external(FIRMWARE, "004")
    EXTERNAL_FIRMWARE_INVALID_MODEL_FILE = external(FIRMWARE, "005")
    EXTERNAL_FIRMWARE_FILE_NOT_EXISTS = external(FIRMWARE, "006")
    EXTERNAL_FIRMWARE_INVALID_APPLICATION_FIRMWARE = external(FIRMWARE, "007")
    EXTERNAL_FIRMWARE_INVALID_SENSOR_FIRMWARE = external(FIRMWARE, "008")
    EXTERNAL_DEVICE_NAMES_TOO_LONG = external(FIRMWARE, "009")

    def is_internal(self) -> bool:
        return self.value.startswith(INTERNAL)

    def is_subtype(self, type: str) -> bool:
        return self.value[1:3] == type
