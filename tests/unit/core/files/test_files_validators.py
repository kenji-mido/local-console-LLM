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
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import call
from unittest.mock import MagicMock

import pytest
from local_console.core.camera.firmware import UserException
from local_console.core.error.code import ErrorCodes
from local_console.core.files.files_validators import AlreadyExistsValidator
from local_console.core.files.files_validators import app_validator
from local_console.core.files.files_validators import ChainOfValidators
from local_console.core.files.files_validators import FirmwareValidator
from local_console.core.files.files_validators import model_validator
from local_console.core.files.files_validators import NoneEmptyValidator
from local_console.core.files.values import FileType
from local_console.utils.validation import AOT_XTENSA_HEADER
from local_console.utils.validation import IMX500_MODEL_HEADER

from tests.strategies.samplers.files import FileInfoSampler
from tests.strategies.samplers.files import ValidableFileInfoSampler


def test_chain_of_validators_call_all():
    mocked_validator = MagicMock()
    chained = ChainOfValidators(validators=[mocked_validator, mocked_validator])
    sample = FileInfoSampler().sample()
    chained(sample)

    mocked_validator.validate.assert_has_calls([call(sample), call(sample)])


def test_chain_of_validators_call_validable():
    mocked_validator = MagicMock()
    mocked_non_validable = MagicMock()
    mocked_non_validable.validable.return_value = False
    chained = ChainOfValidators(
        validators=[
            mocked_non_validable,
            mocked_validator,
            mocked_non_validable,
            mocked_validator,
        ]
    )
    sample = FileInfoSampler().sample()
    chained(sample)

    mocked_validator.validate.assert_has_calls([call(sample), call(sample)])
    mocked_non_validable.validate.assert_not_called()


def test_firmware_validable():
    sampler = FileInfoSampler(type=FileType.FIRMWARE, path=Path("sample.zip"))
    validator = FirmwareValidator()
    assert validator.validable(sampler.sample())
    for type in FileType:
        if type != FileType.FIRMWARE:
            sampler.type = type
            assert not validator.validable(sampler.sample())


def test_firmware_validate_type():
    validate = FirmwareValidator()
    extensions = [".fpk", ".bin"]
    for extension in extensions:
        sampler = FileInfoSampler(
            type=FileType.FIRMWARE, path=Path("sample" + extension)
        )
        validate(sampler.sample())

    extensions = [".zip", ".tflite", ".exe", ".py"]
    for extension in extensions:
        with pytest.raises(
            UserException, match="Invalid Application Firmware!"
        ) as error:
            sampler.path = Path("sample" + extension)
            validate(sampler.sample())
        assert (
            error.value.code
            == ErrorCodes.EXTERNAL_FIRMWARE_INVALID_APPLICATION_FIRMWARE
        )


def test_model_validable():
    valids = [FileType.MODEL, FileType.MODEL_RAW]
    sampler = ValidableFileInfoSampler()
    validator = model_validator()
    for type in FileType:
        sampler.type = type
        if type in valids:
            assert validator.validable(sampler.sample())
        else:
            sampler.type = type
            assert not validator.validable(sampler.sample())


def test_model_validate_content():
    validator = model_validator()
    sampler = ValidableFileInfoSampler()
    sampler.content = bytes(IMX500_MODEL_HEADER)
    validator.validate(sampler.sample())


@pytest.mark.parametrize("content", [b"", b"Invalid", bytes(IMX500_MODEL_HEADER[:-1])])
def test_model_invalids_content(content: bytes):
    validator = model_validator()
    sampler = ValidableFileInfoSampler()
    with pytest.raises(UserException, match="Invalid Model!") as error:
        sampler.content = content
        validator(sampler.sample())

    assert error.value.code == ErrorCodes.EXTERNAL_FIRMWARE_INVALID_MODEL_FILE


def test_app_validate_content():
    validator = app_validator()
    sampler = ValidableFileInfoSampler()
    sampler.content = bytes(AOT_XTENSA_HEADER)
    validator.validate(sampler.sample())


def test_app_invalids_content():
    validator = app_validator()
    sampler = ValidableFileInfoSampler()
    with pytest.raises(UserException, match="Invalid App!") as error:
        sampler.content = b"Invalid"
        validator(sampler.sample())

    assert error.value.code == ErrorCodes.EXTERNAL_FIRMWARE_INVALID_APP_FILE


@pytest.mark.parametrize("type", FileType)
def test_empty_file_acceptall(type: FileType):
    validator = NoneEmptyValidator()

    assert validator.validable(type)


def test_empty_file_check():
    validator = NoneEmptyValidator()
    sample = ValidableFileInfoSampler(content=b"").sample()
    with pytest.raises(UserException, match="File is empty") as error:
        validator(sample)

    assert error.value.code == ErrorCodes.EXTERNAL_EMPTY_FILE


@pytest.mark.parametrize("type", FileType)
def test_already_exists_acceptall(type: FileType):
    validator = AlreadyExistsValidator()

    assert validator.validable(type)


def test_already_exists() -> None:
    validator = AlreadyExistsValidator()
    with TemporaryDirectory(
        prefix="dropthis", ignore_cleanup_errors=True
    ) as temporary_dir:
        existing_path: Path = Path(temporary_dir) / "sample.bin"
        existing_path.write_text("Existing content")
        sample = ValidableFileInfoSampler(path=existing_path)
        with pytest.raises(UserException, match="File already existing") as error:
            validator(sample)

        assert error.value.code == ErrorCodes.EXTERNAL_FILE_ALREADY_EXISTS
