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
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.camera.enums import OTAUpdateStatus
from local_console.core.camera.firmware import FirmwareValidationStatus
from local_console.core.camera.firmware import validate_firmware_file
from local_console.core.commands.ota_deploy import get_package_hash
from local_console.core.error.code import ErrorCodes
from local_console.core.schemas.edge_cloud_if_v1 import DnnOta
from local_console.core.schemas.edge_cloud_if_v1 import DnnOtaBody

from tests.fixtures.camera import cs_init
from tests.fixtures.firmware import mock_get_ota_update_status
from tests.strategies.samplers.device_config import DeviceConfigurationSampler


@pytest.fixture(params=["Application Firmware", "Sensor Firmware"])
def firmware_type(request):
    return request.param


@pytest.fixture(params=["Done", "Failed"])
def update_status(request):
    return request.param


@pytest.mark.trio
async def test_select_path(tmp_path, cs_init) -> None:
    """
    Test how selection of file path and type results in
    hash computation and determining validity of the file,
    both in the state variables and proxy properties.
    """
    state = cs_init
    state._init_bindings()

    app_fw_filename = "ota.bin"
    app_fw_file_path = tmp_path / app_fw_filename
    sensor_fw_filename = "firmware.fpk"
    sensor_fw_file_path = tmp_path / sensor_fw_filename

    # Create dummy firmware files and hashes
    app_fw_file_path.write_text("dummy")
    app_fw_file_hash = get_package_hash(app_fw_file_path)

    sensor_fw_file_path.write_text("foobar")
    sensor_fw_file_hash = get_package_hash(sensor_fw_file_path)

    # Select Application Firmware
    state.firmware_file_type.value = OTAUpdateModule.APFW
    state.firmware_file.value = app_fw_file_path
    assert state.firmware_file_hash.value == app_fw_file_hash
    assert state.firmware_file_valid.value

    # Switch path to not match its type
    state.firmware_file.value = sensor_fw_file_path
    assert not state.firmware_file_valid.value

    # Select Sensor Firmware
    state.firmware_file_type.value = OTAUpdateModule.SENSORFW
    state.firmware_file.value = sensor_fw_file_path
    assert state.firmware_file_hash.value == sensor_fw_file_hash
    assert state.firmware_file_valid.value

    # Switch path to not match its type
    state.firmware_file.value = app_fw_file_path
    assert not state.firmware_file_valid.value


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
    a_config = DeviceConfigurationSampler().sample()

    # Check what happens when passing an inexistent file
    inexistent_file = tmp_path / "i_dont_exist"
    assert not inexistent_file.exists()
    with pytest.raises(UserException, match="Firmware file does not exist!") as error:
        validate_firmware_file(
            inexistent_file, OTAUpdateModule.APFW, "", current_cfg=a_config
        )
    assert error.value.code == ErrorCodes.EXTERNAL_FIRMWARE_FILE_NOT_EXISTS

    # Check what happens when device configuration is not available
    with (patch("local_console.core.camera.firmware.logger") as mock_logger,):
        assert (
            validate_firmware_file(
                app_fw_file_path, OTAUpdateModule.APFW, "", current_cfg=None
            )
            == FirmwareValidationStatus.INVALID
        )
        mock_logger.debug.assert_called_once_with("DeviceConfiguration is None.")

    # Test Application Firmware on mismatched file with the set type
    with pytest.raises(UserException, match="Invalid Application Firmware!") as error:
        validate_firmware_file(
            sensor_fw_file_path, OTAUpdateModule.APFW, "irrelevant", a_config
        )
    assert error.value.code == ErrorCodes.EXTERNAL_FIRMWARE_INVALID_APPLICATION_FIRMWARE

    # Test matching file and type and version equal to a_config.Version.ApFwVersion
    with (patch("local_console.core.camera.firmware.logger") as mock_logger,):
        version = a_config.Version.ApFwVersion
        validation_result: FirmwareValidationStatus = validate_firmware_file(
            app_fw_file_path, OTAUpdateModule.APFW, version, a_config
        )
        assert validation_result == FirmwareValidationStatus.SAME_FIRMWARE
        mock_logger.debug.assert_called_once_with(
            "Received firmware is the same as the one currently installed in the device."
        )

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

    # Test matching file and type and version equal to a_config.Version.ApFwVersion
    with (patch("local_console.core.camera.firmware.logger") as mock_logger,):
        a_config.Version.SensorFwVersion = "010707"
        version = a_config.Version.SensorFwVersion
        assert (
            validate_firmware_file(
                sensor_fw_file_path, OTAUpdateModule.SENSORFW, version, a_config
            )
            == FirmwareValidationStatus.SAME_FIRMWARE
        )
        mock_logger.debug.assert_called_once_with(
            "Received firmware is the same as the one currently installed in the device."
        )

    # Test matching file and type and a different version
    assert (
        validate_firmware_file(
            sensor_fw_file_path, OTAUpdateModule.SENSORFW, "010300", a_config
        )
        == FirmwareValidationStatus.VALID
    )


@pytest.mark.trio
async def test_update_firmware_task_invalid(tmp_path, cs_init) -> None:

    from local_console.core.camera.firmware import update_firmware_task

    from local_console.core.error.base import UserException
    from local_console.core.error.code import ErrorCodes

    camera_state = cs_init
    error_notify = Mock()
    with (
        patch.object(camera_state, "ota_event") as mock_ota_event,
        patch(
            "local_console.core.camera.firmware.validate_firmware_file",
            side_effect=UserException(
                ErrorCodes.EXTERNAL_FIRMWARE_INVALID_APPLICATION_FIRMWARE,
                "invalid file",
            ),
        ),
    ):
        # Pretend these values are meaningful
        camera_state.firmware_file.value = tmp_path / "some file"
        camera_state.firmware_file_type.value = "some type"
        camera_state.firmware_file_version.value = "some version"

        await update_firmware_task(camera_state, error_notify)
        mock_ota_event.assert_not_awaited()
        error_notify.assert_called_once_with("invalid file")


@pytest.mark.trio
@pytest.mark.parametrize(
    "ota_type,initial_status,final_status",
    [
        ("ApFw", OTAUpdateStatus.DONE, OTAUpdateStatus.DONE),
        ("ApFw", OTAUpdateStatus.FAILED, OTAUpdateStatus.DONE),
        ("ApFw", OTAUpdateStatus.FAILED, OTAUpdateStatus.FAILED),
        ("ApFw", OTAUpdateStatus.DONE, OTAUpdateStatus.FAILED),
        ("ApFw", OTAUpdateStatus.DOWNLOADING, OTAUpdateStatus.FAILED),
        ("ApFw", OTAUpdateStatus.UPDATING, OTAUpdateStatus.FAILED),
        ("ApFw", OTAUpdateStatus.DOWNLOADING, OTAUpdateStatus.DONE),
        ("ApFw", OTAUpdateStatus.UPDATING, OTAUpdateStatus.DONE),
        ("SensorFw", OTAUpdateStatus.DONE, OTAUpdateStatus.DONE),
        ("SensorFw", OTAUpdateStatus.FAILED, OTAUpdateStatus.DONE),
        ("SensorFw", OTAUpdateStatus.FAILED, OTAUpdateStatus.FAILED),
        ("SensorFw", OTAUpdateStatus.DONE, OTAUpdateStatus.FAILED),
        ("SensorFw", OTAUpdateStatus.DOWNLOADING, OTAUpdateStatus.FAILED),
        ("SensorFw", OTAUpdateStatus.UPDATING, OTAUpdateStatus.FAILED),
        ("SensorFw", OTAUpdateStatus.DOWNLOADING, OTAUpdateStatus.DONE),
        ("SensorFw", OTAUpdateStatus.UPDATING, OTAUpdateStatus.DONE),
    ],
)
async def test_update_firmware_task_valid(
    tmp_path, cs_init, ota_type, initial_status, final_status
) -> None:

    from local_console.core.camera.firmware import update_firmware_task

    from local_console.core.camera.enums import OTAUpdateModule

    camera_state = cs_init

    error_notify = Mock()

    extension = "bin" if ota_type == "ApFw" else "fpk"
    filename = f"dummy_ota.{extension}"
    app_fw_file_path = tmp_path / filename
    app_fw_file_path.write_text("dummy")
    camera_state.firmware_file.value = app_fw_file_path
    camera_state.firmware_file_type.value = OTAUpdateModule(ota_type)
    camera_state.firmware_file_version.value = "ABCDEF"

    # Set the end state
    camera_state.device_config.value = DeviceConfigurationSampler().sample()
    camera_state.mqtt_port.value = 1883

    mock_agent = MagicMock()
    mock_agent.mqtt_scope.return_value = AsyncMock()
    mock_agent.configure = AsyncMock()

    mock_server = AsyncMock()
    mock_server.__aenter__.return_value.port = 8000

    hashvalue = get_package_hash(app_fw_file_path)
    payload = DnnOta(
        OTA=DnnOtaBody(
            UpdateModule=ota_type,
            DesiredVersion=camera_state.firmware_file_version.value,
            PackageUri=f"http://1.1.1.1:8000/{filename}",
            HashValue=hashvalue,
        )
    ).model_dump_json()

    sequence_updates = [
        initial_status,
        OTAUpdateStatus.DOWNLOADING,
        OTAUpdateStatus.DOWNLOADING,
        OTAUpdateStatus.DOWNLOADING,
        OTAUpdateStatus.UPDATING,
        final_status,
    ]

    with (
        patch.object(camera_state, "ota_event") as mock_ota_event,
        patch("local_console.core.camera.firmware.Agent", return_value=mock_agent),
        patch(
            "local_console.core.camera.firmware.AsyncWebserver",
            return_value=mock_server,
        ),
        patch(
            "local_console.core.camera.firmware.get_webserver_ip",
            return_value="1.1.1.1",
        ),
        mock_get_ota_update_status(sequence_updates),
    ):

        await update_firmware_task(camera_state, error_notify)

        mock_agent.configure.assert_awaited_once_with(
            "backdoor-EA_Main", "placeholder", payload
        )
        assert len(mock_ota_event.mock_calls) == len(sequence_updates) - 1
        if sequence_updates[-1] == OTAUpdateStatus.DONE:
            error_notify.assert_not_called()
        else:
            error_notify.assert_called()
