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
from local_console.core.files.files_validators import AOTAppValidator
from local_console.core.files.files_validators import ChainOfValidators
from local_console.core.files.files_validators import FirmwareValidator
from local_console.core.files.files_validators import IMX500ModelPkgValidator
from local_console.core.files.files_validators import IMX500ModelRpkValidator
from local_console.core.files.files_validators import NoneEmptyValidator
from local_console.core.files.files_validators import PythonAppValidator
from local_console.core.files.files_validators import WASMAppValidator
from local_console.core.files.values import FileType
from local_console.utils.validation.aot import AOT_HEADER
from local_console.utils.validation.imx500 import IMX500_MODEL_PKG_HEADER
from local_console.utils.validation.imx500 import IMX500_MODEL_RPK_HEADER

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


@pytest.mark.parametrize(
    "extension, validator",
    [("pkg", IMX500ModelPkgValidator()), ("rpk", IMX500ModelRpkValidator())],
)
def test_model_validable(extension, validator):
    valids = [FileType.MODEL, FileType.MODEL_RAW]
    sampler = ValidableFileInfoSampler(path=Path(f"/some/model.{extension}"))
    for type in FileType:
        sampler.type = type
        if type in valids:
            assert validator.validable(sampler.sample())
        else:
            sampler.type = type
            assert not validator.validable(sampler.sample())


def test_model_pkg_validate_content():
    validator = IMX500ModelPkgValidator()
    sampler = ValidableFileInfoSampler()
    sampler.content = bytes(IMX500_MODEL_PKG_HEADER)
    validator.validate(sampler.sample())


def test_model_rpk_validate_content():
    validator = IMX500ModelRpkValidator()
    sampler = ValidableFileInfoSampler()
    sampler.content = bytes(IMX500_MODEL_RPK_HEADER)
    validator.validate(sampler.sample())


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"Invalid",
        bytes(IMX500_MODEL_PKG_HEADER[:-1]),
        bytes(IMX500_MODEL_RPK_HEADER[:-1]),
    ],
)
@pytest.mark.parametrize(
    "validator", [IMX500ModelPkgValidator(), IMX500ModelRpkValidator()]
)
def test_model_pkg_invalids_content(content: bytes, validator):
    sampler = ValidableFileInfoSampler()
    with pytest.raises(UserException, match="Invalid Model!") as error:
        sampler.content = content
        validator(sampler.sample())

    assert error.value.code == ErrorCodes.EXTERNAL_FIRMWARE_INVALID_MODEL_FILE


def test_app_aot_validate_content():
    validator = AOTAppValidator()
    sampler = ValidableFileInfoSampler()
    sampler.content = bytes(AOT_HEADER)
    validator.validate(sampler.sample())


def test_app_aot_aarch64_invalid_content():
    validator = AOTAppValidator()
    sampler = ValidableFileInfoSampler()
    with pytest.raises(UserException, match="Invalid AoT application object!") as error:
        sampler.content = b"Invalid"
        validator(sampler.sample())

    assert error.value.code == ErrorCodes.EXTERNAL_FIRMWARE_INVALID_APP_FILE


def test_app_aot_xtensa_invalid_content():
    validator = AOTAppValidator()
    sampler = ValidableFileInfoSampler()
    with pytest.raises(UserException, match="Invalid AoT application object!") as error:
        sampler.content = b"Invalid"
        validator(sampler.sample())

    assert error.value.code == ErrorCodes.EXTERNAL_FIRMWARE_INVALID_APP_FILE


def test_app_python_validate_content(tmp_path):
    validator = PythonAppValidator()

    test_file = tmp_path / "good_script.py"
    sampler = ValidableFileInfoSampler(path=test_file)
    sampler.content = b"import sys; print(f'valid python: {2+2}', file=sys.stderr)"
    validator.validate(sampler.sample())


def test_app_python_invalid_content(tmp_path):
    validator = PythonAppValidator()

    test_file = tmp_path / "bad_script.py"
    sampler = ValidableFileInfoSampler(path=test_file)
    sampler.content = b"import java.lib.machine.arch.processor.alu.operations.sum; class MyClass { public static void main(String[] args) { System.out.println(sum(2, 2)); } }"

    with pytest.raises(UserException, match="Invalid application object!") as error:
        validator(sampler.sample())

    assert error.value.code == ErrorCodes.EXTERNAL_FIRMWARE_INVALID_APP_FILE


def test_app_wasm_validate_content():
    validator = WASMAppValidator()

    test_file = (
        Path(__file__).parents[4]
        / "local-console-ui/ui-tests/tools/samples/wasm/classification.wasm"
    )
    sampler = ValidableFileInfoSampler(path=test_file)
    sampler.content = test_file.read_bytes()
    validator.validate(sampler.sample())


def test_app_wasm_invalid_content(tmp_path):
    validator = WASMAppValidator()

    test_file = tmp_path / "wrong_module.wasm"
    sampler = ValidableFileInfoSampler(path=test_file)
    sampler.content = b"booboo"

    with pytest.raises(UserException, match="Invalid application object!") as error:
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
