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
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

import pytest
import trio
from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.camera.firmware import FirmwareHeader
from local_console.core.camera.firmware import FirmwareValidationStatus
from local_console.core.camera.firmware import process_firmware_file
from local_console.core.camera.firmware import update_firmware_task
from local_console.core.camera.firmware import validate_firmware_file
from local_console.core.camera.state import CameraState
from local_console.core.deploy.tasks.firmware_task import FirmwareTransientStatus
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes
from local_console.utils.trio import EVENT_WAITING

from tests.fixtures.agent import mocked_agent
from tests.mocks.http import mocked_http_server
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
        state = CameraState(MagicMock(), MagicMock())
        firmware_file = current_dir / "firmware_without_header.bin"
        state.firmware_file_type.value = OTAUpdateModule.APFW
        state.firmware_file.value = firmware_file
        result, header = process_firmware_file(tmp, state)

        assert result == tmp / "firmware_without_header.bin"
        assert header is None
        assert firmware_file.read_bytes() == result.read_bytes()


def test_header_just_copy_without_header():
    with TemporaryDirectory() as temporal:
        tmp = Path(temporal)
        current_dir = Path(__file__).parent
        state = CameraState(MagicMock(), MagicMock())
        without_header = current_dir / "firmware_without_header.bin"
        firmware_file = current_dir / "firmware_with_header.bin"
        state.firmware_file_type.value = OTAUpdateModule.APFW
        state.firmware_file.value = firmware_file
        processed_file, header = process_firmware_file(tmp, state)

        expected_file = tmp / "firmware_with_header.no_header.bin"
        assert header == FirmwareHeader(
            header_version="020000", cloud_version="010000", firmware_version="0700FAPD"
        )
        assert without_header.read_bytes() == expected_file.read_bytes()
        assert processed_file == expected_file


def test_header_of_small_file():
    with TemporaryDirectory() as first_tmp, TemporaryDirectory() as temporal:
        tmp = Path(temporal)
        state = CameraState(MagicMock(), MagicMock())
        firmware_file = Path(first_tmp) / "small.bin"
        firmware_file.write_text("small")
        state.firmware_file_type.value = OTAUpdateModule.APFW
        state.firmware_file.value = firmware_file
        result, header = process_firmware_file(tmp, state)

        assert header is None
        assert "small" == result.read_text()
        assert result == tmp / "small.bin"


@pytest.mark.trio
async def test_use_firmware_from_file():
    with mocked_agent() as agent, mocked_http_server() as http:
        current_dir = Path(__file__).parent
        state = CameraState(MagicMock(), MagicMock())
        state.mqtt_port.value = 1883
        state.firmware_file.value = current_dir / "firmware_with_header.bin"
        state.firmware_file_version.value = "willBeOverwritten"
        state.firmware_file_type.value = OTAUpdateModule.APFW
        state.device_config.value = DeviceConfigurationSampler().sample()
        no_error = True

        def call_on_error(message: str) -> None:
            nonlocal no_error
            no_error = False

        async with trio.open_nursery() as nursery:

            nursery.start_soon(
                update_firmware_task, state, FirmwareTransientStatus, call_on_error
            )

            await EVENT_WAITING.wait_for(lambda: agent.agent.configure.await_count > 0)
            args = json.loads(agent.agent.configure.await_args[0][2])
            assert args["OTA"]["DesiredVersion"] == "0700FAPD"
            url: str = args["OTA"]["PackageUri"]
            downloaded_file_name = url.split("/")[-1]
            assert downloaded_file_name == "firmware_with_header.no_header.bin"
            web_base_path: Path = http.call_args[0][0]
            downloaded_file = web_base_path / downloaded_file_name
            current_dir = Path(__file__).parent
            without_header = current_dir / "firmware_without_header.bin"
            assert downloaded_file.read_bytes() == without_header.read_bytes()
            nursery.cancel_scope.cancel()


@pytest.mark.parametrize(
    "version",
    [
        None,
        "",
        "TooLongVersionLongerThan32Bytes-1",  # 32 bytes less \0 https://github.com/midokura/EdgeAIPF.smartcamera.type3.mirror/blob/abb41d21f655bc18ba4155bf75b413fdc1cc10ad/src/setting/setting_config.c#L651-L660 https://github.com/SonySemiconductorSolutions/EdgeAIPF.smartcamera.type3.mirror/blob/2a2edf5f3a31ba75ccf2432f7197cc55d7fbad94/ptd-porting/src/imx_app/include/nx_adp/app_desc_nx_adp.h https://midokura.slack.com/archives/C05T5523QJJ/p1729586068305889
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
        firmware_file, OTAUpdateModule.APFW, "ENDSINPD", config
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
        firmware_file, OTAUpdateModule.APFW, "ENDSINPD", config, header
    )

    assert result == FirmwareValidationStatus.VALID
