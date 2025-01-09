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
from abc import ABC
from abc import abstractmethod
from typing import Generic
from typing import TypeVar

from local_console.core.camera.enums import FirmwareExtension
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes
from local_console.core.files.values import FileInfo
from local_console.core.files.values import FileType
from local_console.utils.validation import AOT_XTENSA_HEADER
from local_console.utils.validation import IMX500_MODEL_HEADER


class ValidableFileInfo(FileInfo):
    content: bytes

    def to_file_info(self) -> FileInfo:
        return FileInfo(**self.model_dump())


INPUT = TypeVar("INPUT", bound=FileInfo)


class ChainableValidator(ABC, Generic[INPUT]):

    @abstractmethod
    def validate(self, info: INPUT) -> None:
        """
        Subclasses must implement this method to perform specific validation checks
        on the provided FileInfo object. For each validation error, a custom exception
        should be raised to indicate the specific issue.
        """
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def validable(self, info: INPUT) -> bool:
        """
        Subclasses must implement this method to check if validate function can
        be checked with the current content. If is not validable it will not be called.
        """
        raise NotImplementedError("Subclasses must implement this method")

    def __call__(self, info: INPUT) -> None:
        self.validate(info)


class ChainOfValidators(Generic[INPUT]):
    def __init__(self, validators: list[ChainableValidator[INPUT]]):
        self.validators = validators

    def __call__(self, info: INPUT) -> None:
        for validator in self.validators:
            if validator.validable(info):
                validator.validate(info)


class FirmwareValidator(ChainableValidator[ValidableFileInfo]):
    def validable(self, info: ValidableFileInfo) -> bool:
        return info.type == FileType.FIRMWARE

    def validate(self, info: FileInfo) -> None:
        if info.path.suffix not in [
            FirmwareExtension.APPLICATION_FW,
            FirmwareExtension.SENSOR_FW,
        ]:
            raise UserException(
                ErrorCodes.EXTERNAL_FIRMWARE_INVALID_APPLICATION_FIRMWARE,
                "Invalid Application Firmware!",
            )


class CheckFirstBytesValidator(ChainableValidator[ValidableFileInfo]):
    def __init__(
        self,
        header_bytes: bytes,
        types: list[FileType],
        error_message: str,
        error_code: ErrorCodes,
    ) -> None:
        super().__init__()
        self.header_bytes = header_bytes
        self.types = types
        self.error_message = error_message
        self.error_code = error_code

    def validable(self, info: ValidableFileInfo) -> bool:
        return info.type in self.types

    def validate(self, info: ValidableFileInfo) -> None:
        if info.content[: len(self.header_bytes)] != self.header_bytes:
            raise UserException(
                self.error_code,
                self.error_message,
            )


class NoneEmptyValidator(ChainableValidator[ValidableFileInfo]):
    def validable(self, info: ValidableFileInfo) -> bool:
        return True

    def validate(self, info: ValidableFileInfo) -> None:
        if not info.content:
            raise UserException(
                ErrorCodes.EXTERNAL_EMPTY_FILE,
                "File is empty",
            )


class AlreadyExistsValidator(ChainableValidator[FileInfo]):
    def validable(self, info: FileInfo) -> bool:
        return True

    def validate(self, info: FileInfo) -> None:
        if info.path.exists():
            raise UserException(
                ErrorCodes.EXTERNAL_FILE_ALREADY_EXISTS,
                "File already existing",
            )


def app_validator() -> CheckFirstBytesValidator:
    return CheckFirstBytesValidator(
        bytes(AOT_XTENSA_HEADER),
        [FileType.APP, FileType.APP_RAW],
        "Invalid App!",
        ErrorCodes.EXTERNAL_FIRMWARE_INVALID_APP_FILE,
    )


def model_validator() -> CheckFirstBytesValidator:
    return CheckFirstBytesValidator(
        bytes(IMX500_MODEL_HEADER),
        [FileType.MODEL, FileType.MODEL_RAW],
        "Invalid Model!",
        ErrorCodes.EXTERNAL_FIRMWARE_INVALID_MODEL_FILE,
    )


def save_validator() -> ChainOfValidators:
    return ChainOfValidators(
        [
            NoneEmptyValidator(),
            AlreadyExistsValidator(),
            FirmwareValidator(),
            model_validator(),
            app_validator(),
        ]
    )
