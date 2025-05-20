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

import pytest
from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.camera.firmware import FirmwareHeader
from local_console.core.camera.firmware import FirmwareInfo
from local_console.core.camera.firmware import FirmwareValidationStatus
from local_console.core.camera.firmware import process_firmware_file
from local_console.core.camera.firmware import validate_firmware_file
from local_console.core.camera.states.v1.common import populate_properties
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes

from tests.strategies.samplers.device_config import DeviceConfigurationSampler


@pytest.mark.parametrize("invalid", ["12345", "1234567"])
def test_invalid_header_six_chars(invalid: str):
    valid_version = "123456"
    with pytest.raises(UserException) as e:
        FirmwareHeader(
            header_version=invalid,
            cloud_version=valid_version,
            firmware_version="12345678",
        )

    assert str(e.value) == "Header version should have 6 characters"
    assert e.value.code == ErrorCodes.EXTERNAL_FIRMWARE_VERSION_6_CHARS

    with pytest.raises(UserException) as e:
        FirmwareHeader(
            header_version=valid_version,
            cloud_version=invalid,
            firmware_version="12345678",
        )

    assert str(e.value) == "Cloud version should have 6 characters"
    assert e.value.code == ErrorCodes.EXTERNAL_FIRMWARE_VERSION_6_CHARS


@pytest.mark.parametrize("invalid", ["1234567", "123456789"])
def test_invalid_header_firmware_chars(invalid: str):
    valid_version = "123456"
    with pytest.raises(UserException) as e:
        FirmwareHeader(
            header_version=valid_version,
            cloud_version=valid_version,
            firmware_version=invalid,
        )

    assert str(e.value) == "Firmware version should have 8 characters"
    assert e.value.code == ErrorCodes.EXTERNAL_FIRMWARE_VERSION_8_CHARS


@pytest.mark.parametrize(
    "invalid",
    ["%%0200000100000700FAPDFFFFFFFFF", "%%0200000100000700FAPDFFFFFFFFFFF", "", None],
)
def test_parse_header_invalid(invalid: str | None):
    assert not FirmwareHeader.parse(invalid)


def test_parse_header():
    assert FirmwareHeader.parse("%%0200000100000700FAPDFFFFFFFFFF") == FirmwareHeader(
        header_version="020000", cloud_version="010000", firmware_version="0700FAPD"
    )


def test_no_header_just_copy():
    with TemporaryDirectory() as temporal:
        tmp = Path(temporal)
        current_dir = Path(__file__).parent
        firmware_file = current_dir / "firmware_without_header.bin"

        firmware_info = FirmwareInfo(
            path=firmware_file,
            hash="",
            version="willBeOverwritten",
            type=OTAUpdateModule.APFW,
            is_valid=True,
        )

        result, header = process_firmware_file(tmp, firmware_info)

        assert result == tmp / "firmware_without_header.bin"
        assert header is None
        assert firmware_file.read_bytes() == result.read_bytes()


def test_header_just_copy_without_header():
    with TemporaryDirectory() as temporal:
        tmp = Path(temporal)
        current_dir = Path(__file__).parent
        without_header = current_dir / "firmware_without_header.bin"
        firmware_file = current_dir / "firmware_with_header.bin"

        firmware_info = FirmwareInfo(
            path=firmware_file,
            hash="",
            version="willBeOverwritten",
            type=OTAUpdateModule.APFW,
            is_valid=True,
        )

        processed_file, header = process_firmware_file(tmp, firmware_info)

        expected_file = tmp / "firmware_with_header.no_header.bin"
        assert header == FirmwareHeader(
            header_version="020000", cloud_version="010000", firmware_version="0700FAPD"
        )
        assert without_header.read_bytes() == expected_file.read_bytes()
        assert processed_file == expected_file


def test_header_of_small_file():
    with TemporaryDirectory() as first_tmp, TemporaryDirectory() as temporal:
        tmp = Path(temporal)
        firmware_file = Path(first_tmp) / "small.bin"
        firmware_file.write_text("small")

        firmware_info = FirmwareInfo(
            path=firmware_file,
            hash="",
            version="willBeOverwritten",
            type=OTAUpdateModule.APFW,
            is_valid=True,
        )

        result, header = process_firmware_file(tmp, firmware_info)

        assert header is None
        assert "small" == result.read_text()
        assert result == tmp / "small.bin"


@pytest.mark.parametrize(
    "version",
    [
        None,
        "",
        "TooLongVersionLongerThan32Bytes-1",  # 32 bytes less \0
    ],
)
def test_invalid_version(version: str):
    current_dir = Path(__file__).parent
    firmware_file = current_dir / "firmware_with_header.bin"
    config = DeviceConfigurationSampler().sample()
    result = validate_firmware_file(
        firmware_file, OTAUpdateModule.APFW, version, config
    )

    assert result == FirmwareValidationStatus.INVALID


def test_dts_968_rayprus_pd_ending():
    current_dir = Path(__file__).parent
    firmware_file = current_dir / "firmware_with_header.bin"
    config = DeviceConfigurationSampler().sample()
    result = validate_firmware_file(
        firmware_file, OTAUpdateModule.APFW, "ENDSINPD", populate_properties(config)
    )

    assert result == FirmwareValidationStatus.INVALID


def test_dts_968_rayprus_pd_ending_from_header():
    current_dir = Path(__file__).parent
    firmware_file = current_dir / "firmware_with_header.bin"
    config = DeviceConfigurationSampler().sample()
    header = FirmwareHeader(
        header_version="123456", cloud_version="123456", firmware_version="ENDSINPD"
    )
    result = validate_firmware_file(
        firmware_file,
        OTAUpdateModule.APFW,
        "ENDSINPD",
        populate_properties(config),
        header,
    )

    assert result == FirmwareValidationStatus.VALID
