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
CONFIG = "21"


def code(source: str, kind: str, detail: str) -> str:
    code = f"{source}{kind}{detail}"
    assert int(code)
    return code


def internal(kind: str, detail: str) -> str:
    return code(INTERNAL, kind, detail)


def external(kind: str, detail: str) -> str:
    return code(EXTERNAL, kind, detail)


class ErrorCodes(Enum):
    INTERNAL_GENERIC = internal(GENERIC, "001")  # 001001
    INTERNAL_HTTP = internal(GENERIC, "002")  # 001002
    INTERNAL_PYDANTIC = internal(GENERIC, "003")  # 001003
    INTERNAL_MQTT = internal(GENERIC, "004")  # 001004
    INTERNAL_DEVICE_RPC_MISSING_CLIENT = internal(DEVICE, "001")  # 020001
    INTERNAL_INVALID_ERROR_CODE = internal(ERROR, "001")  # 002001
    INTERNAL_INVALID_USER_CODE = internal(ERROR, "002")  # 002002
    EXTERNAL_NOTFOUND = external(GENERIC, "001")  # 101001
    EXTERNAL_DEPLOYMENT_ALREADY_RUNNING = external(DEPLOYMENT, "001")  # 110001
    EXTERNAL_FIRMWARE_VERSION_6_CHARS = external(FIRMWARE, "001")  # 111001
    EXTERNAL_FIRMWARE_VERSION_8_CHARS = external(FIRMWARE, "002")  # 111002
    EXTERNAL_FIRMWARE_SAME_VERSION = external(FIRMWARE, "003")  # 111003
    EXTERNAL_ONE_DEVICE_NEEDED = external(DEVICE, "001")  # 120001
    EXTERNAL_DEVICE_NAMES_MUST_BE_UNIQUE = external(DEVICE, "002")  # 120002
    EXTERNAL_DEVICE_PORTS_MUST_BE_UNIQUE = external(DEVICE, "003")  # 120003
    EXTERNAL_DEVICE_PORTS_MUST_BE_IN_TCP_RANGE = external(DEVICE, "004")  # 120004
    EXTERNAL_DEVICE_CREATION_VALIDATION = external(DEVICE, "005")  # 120005
    EXTERNAL_DEVICE_PORT_ALREADY_IN_USE = external(DEVICE, "006")  # 120006
    EXTERNAL_DEVICE_NOT_FOUND = external(DEVICE, "007")  # 120007
    EXTERNAL_DEVICE_UNEXPECTED_RPC = external(DEVICE, "008")  # 120008
    EXTERNAL_EMPTY_FILE = external(GENERIC, "004")  # 101004
    EXTERNAL_FILE_ALREADY_EXISTS = external(GENERIC, "005")  # 101005
    EXTERNAL_CANNOT_USE_DIRECTORY = external(GENERIC, "006")  # 101006
    EXTERNAL_FILE_ERROR = external(GENERIC, "007")  # 101007
    EXTERNAL_INVALID_METHOD_DURING_STATE = external(GENERIC, "008")  # 101008
    EXTERNAL_FIRMWARE_INVALID_APP_FILE = external(FIRMWARE, "004")  # 111004
    EXTERNAL_FIRMWARE_INVALID_MODEL_FILE = external(FIRMWARE, "005")  # 111005
    EXTERNAL_FIRMWARE_FILE_NOT_EXISTS = external(FIRMWARE, "006")  # 111006
    EXTERNAL_FIRMWARE_INVALID_APPLICATION_FIRMWARE = external(FIRMWARE, "007")  # 111007
    EXTERNAL_FIRMWARE_INVALID_SENSOR_FIRMWARE = external(FIRMWARE, "008")  # 111008
    EXTERNAL_DEVICE_NAMES_TOO_LONG = external(FIRMWARE, "009")  # 111009
    EXTERNAL_CONFIG_UNITSIZE = external(CONFIG, "001")  # 121001

    def is_internal(self) -> bool:
        return self.value.startswith(INTERNAL)

    def is_subtype(self, type: str) -> bool:
        return self.value[1:3] == type
