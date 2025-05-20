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
from local_console.core.enums import AiModelExtension
from local_console.core.enums import ModuleExtension
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes
from local_console.core.files.values import FileInfo
from local_console.core.files.values import FileType
from local_console.utils.validation.aot import AOT_HEADER
from local_console.utils.validation.imx500 import IMX500_MODEL_PKG_HEADER
from local_console.utils.validation.imx500 import IMX500_MODEL_RPK_HEADER
from local_console.utils.validation.python_script import is_valid_python_script
from local_console.utils.validation.wasm import is_valid_wasm_binary


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

    HEADERS: list[bytes]
    EXTENSIONS: list[str]
    TYPES: list[FileType]
    EXC_CODE: ErrorCodes
    EXC_MSG: str

    def validable(self, info: ValidableFileInfo) -> bool:
        return info.type in self.TYPES and info.path.suffix in self.EXTENSIONS

    def validate(self, info: ValidableFileInfo) -> None:
        matched = False

        for header in self.HEADERS:
            if info.content[: len(header)] == header:
                matched = True
                break

        if not matched:
            raise UserException(
                self.EXC_CODE,
                self.EXC_MSG,
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


class PythonAppValidator(ChainableValidator[ValidableFileInfo]):
    def validable(self, info: ValidableFileInfo) -> bool:
        return (
            info.type == FileType.APP
            and info.path.suffix == ModuleExtension.PY.as_suffix
        )

    def validate(self, info: ValidableFileInfo) -> None:
        if not is_valid_python_script(info.path, info.content):
            raise UserException(
                ErrorCodes.EXTERNAL_FIRMWARE_INVALID_APP_FILE,
                "Invalid application object!",
            )


class WASMAppValidator(ChainableValidator[ValidableFileInfo]):
    def validable(self, info: ValidableFileInfo) -> bool:
        return (
            info.type == FileType.APP
            and info.path.suffix == ModuleExtension.WASM.as_suffix
        )

    def validate(self, info: ValidableFileInfo) -> None:
        if not is_valid_wasm_binary(info.path, info.content):
            raise UserException(
                ErrorCodes.EXTERNAL_FIRMWARE_INVALID_APP_FILE,
                "Invalid application object!",
            )


class AOTAppValidator(CheckFirstBytesValidator):
    HEADERS = [
        bytes(AOT_HEADER),
    ]
    EXTENSIONS = [
        ModuleExtension.AOT.as_suffix,
    ]
    TYPES = [FileType.APP, FileType.APP_RAW]
    EXC_CODE = ErrorCodes.EXTERNAL_FIRMWARE_INVALID_APP_FILE
    EXC_MSG = "Invalid AoT application object!"


class IMX500ModelPkgValidator(CheckFirstBytesValidator):
    HEADERS = [
        bytes(IMX500_MODEL_PKG_HEADER),
    ]
    EXTENSIONS = [AiModelExtension.PKG.as_suffix]
    TYPES = [
        FileType.MODEL,
        FileType.MODEL_RAW,
    ]
    EXC_MSG = "Invalid Model!"
    EXC_CODE = ErrorCodes.EXTERNAL_FIRMWARE_INVALID_MODEL_FILE


class IMX500ModelRpkValidator(IMX500ModelPkgValidator):
    HEADERS = [
        bytes(IMX500_MODEL_RPK_HEADER),
    ]
    EXTENSIONS = [AiModelExtension.RPK.as_suffix]


def save_validator() -> ChainOfValidators:
    return ChainOfValidators(
        [
            NoneEmptyValidator(),
            AlreadyExistsValidator(),
            FirmwareValidator(),
            IMX500ModelPkgValidator(),
            IMX500ModelRpkValidator(),
            AOTAppValidator(),
            PythonAppValidator(),
            WASMAppValidator(),
        ]
    )
