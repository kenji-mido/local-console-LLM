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
import pytest
from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.camera.firmware import FirmwareValidationStatus
from local_console.core.camera.firmware import validate_firmware_file
from local_console.core.camera.states.v1.common import populate_properties
from local_console.core.commands.ota_deploy import get_package_hash
from local_console.core.deploy.tasks.firmware_task import FirmwareTask
from local_console.core.error.code import ErrorCodes
from local_console.core.files.values import FileInfo
from local_console.core.files.values import FileType
from local_console.core.firmwares import Firmware
from local_console.core.firmwares import FirmwareIn

from tests.strategies.samplers.device_config import DeviceConfigurationSampler


@pytest.fixture(params=["Application Firmware", "Sensor Firmware"])
def firmware_type(request):
    return request.param


@pytest.fixture(params=["Done", "Failed"])
def update_status(request):
    return request.param


@pytest.mark.trio
async def test_select_path(tmp_path) -> None:
    """
    Test how selection of file path and type results in
    hash computation and determining validity of the file,
    both in the state variables and proxy properties.
    """
    app_fw_filename = "ota.bin"
    app_fw_file_path = tmp_path / app_fw_filename
    sensor_fw_filename = "firmware.fpk"
    sensor_fw_file_path = tmp_path / sensor_fw_filename

    # Create dummy firmware files and hashes
    app_fw_file_path.write_text("dummy")
    app_fw_file_hash = get_package_hash(app_fw_file_path)

    sensor_fw_file_path.write_text("foobar")
    sensor_fw_file_hash = get_package_hash(sensor_fw_file_path)

    firmware = Firmware(
        firmware_id="123",
        info=FirmwareIn(
            firmware_type=OTAUpdateModule.APFW, file_id="456", version="789"
        ),
        file=FileInfo(id="456", path=app_fw_file_path, type=FileType.FIRMWARE),
    )
    # Select Application Firmware
    firmware_info = FirmwareTask._prepare_firmware_info(firmware)
    assert firmware_info.hash == app_fw_file_hash
    assert firmware_info.is_valid

    # Switch path to not match its type
    firmware.file.path = sensor_fw_file_path
    firmware_info = FirmwareTask._prepare_firmware_info(firmware)
    assert not firmware_info.is_valid

    # Select Sensor Firmware
    firmware.info.firmware_type = OTAUpdateModule.SENSORFW
    firmware_info = FirmwareTask._prepare_firmware_info(firmware)
    assert firmware_info.hash == sensor_fw_file_hash
    assert firmware_info.is_valid

    # Switch path to not match its type
    firmware.file.path = app_fw_file_path
    firmware_info = FirmwareTask._prepare_firmware_info(firmware)
    assert not firmware_info.is_valid


def test_validate_firmware_file(tmp_path):
    """
    Test how selection of file path and type results in
    hash computation and determining validity of the file,
    both in the state variables and proxy properties.
    """
    from local_console.core.error.base import UserException

    # Create dummy firmware files
    app_fw_file_path = tmp_path / "ota.bin"
    app_fw_file_path.write_text("dummy")
    sensor_fw_file_path = tmp_path / "firmware.fpk"
    sensor_fw_file_path.write_text("foobar")

    # For firmware validation, update report values in device config are irrelevant
    a_config = populate_properties(DeviceConfigurationSampler().sample())

    # Check what happens when passing an inexistent file
    inexistent_file = tmp_path / "i_dont_exist"
    assert not inexistent_file.exists()
    with pytest.raises(UserException, match="Firmware file does not exist!") as error:
        validate_firmware_file(
            inexistent_file, OTAUpdateModule.APFW, "", current_cfg=a_config
        )
    assert error.value.code == ErrorCodes.EXTERNAL_FIRMWARE_FILE_NOT_EXISTS

    # Test Application Firmware on mismatched file with the set type
    with pytest.raises(UserException, match="Invalid Application Firmware!") as error:
        validate_firmware_file(
            sensor_fw_file_path, OTAUpdateModule.APFW, "irrelevant", a_config
        )
    assert error.value.code == ErrorCodes.EXTERNAL_FIRMWARE_INVALID_APPLICATION_FIRMWARE

    # Test matching file and type and a different version
    assert (
        validate_firmware_file(
            app_fw_file_path, OTAUpdateModule.APFW, "D700T0", a_config
        )
        == FirmwareValidationStatus.VALID
    )

    # Test Sensor Firmware on mismatched file with the set type
    with pytest.raises(UserException, match="Invalid Sensor Firmware!") as error:
        validate_firmware_file(
            app_fw_file_path, OTAUpdateModule.SENSORFW, "irrelevant", a_config
        )
    assert error.value.code == ErrorCodes.EXTERNAL_FIRMWARE_INVALID_SENSOR_FIRMWARE

    # Test matching file and type and a different version
    assert (
        validate_firmware_file(
            sensor_fw_file_path, OTAUpdateModule.SENSORFW, "010300", a_config
        )
        == FirmwareValidationStatus.VALID
    )
