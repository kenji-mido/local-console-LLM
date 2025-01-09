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
import enum
import logging
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable
from typing import Optional

import trio
from local_console.clients.agent import Agent
from local_console.core.camera.enums import FirmwareExtension
from local_console.core.camera.enums import MQTTTopics
from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.camera.enums import OTAUpdateStatus
from local_console.core.camera.state import CameraState
from local_console.core.commands.ota_deploy import configuration_spec
from local_console.core.config import config_obj
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.servers.webserver import AsyncWebserver
from local_console.utils.local_network import get_webserver_ip
from pydantic import BaseModel
from pydantic import field_validator
from pydantic import ValidationInfo

logger = logging.getLogger(__name__)


class TransientStatus:
    """
    A simple holder of values that is updated dynamically during
    a firmware update operation. This present form can be used
    for unit tests, and in the GUI it is subclassed by a type that
    provides automatic event chaining for displaying the current
    status on the screen for the user to get feedback.
    """

    update_status: str = ""
    progress_download: int = 0
    progress_update: int = 0


class FirmwareValidationStatus(enum.Enum):
    VALID = "valid"
    INVALID = "invalid"
    SAME_FIRMWARE = "same_firmware"


class FirmwareHeader(BaseModel):
    header_version: str
    cloud_version: str
    firmware_version: str

    @field_validator("header_version", "cloud_version", mode="before")
    def ensure_six_length(cls, v: str, field: ValidationInfo) -> str:
        if len(v) != 6:
            nice_field_name = (
                field.field_name.replace("_", " ").capitalize()
                if field.field_name
                else "Unknown field"
            )
            raise UserException(
                ErrorCodes.EXTERNAL_FIRMWARE_VERSION_6_CHARS,
                f"{nice_field_name} should have 6 characters",
            )
        return v

    @field_validator("firmware_version", mode="before")
    def ensure_eight_length(cls, v: str, field: ValidationInfo) -> str:
        if len(v) != 8:
            nice_field_name = (
                field.field_name.replace("_", " ").capitalize()
                if field.field_name
                else "Unknown field"
            )
            raise UserException(
                ErrorCodes.EXTERNAL_FIRMWARE_VERSION_8_CHARS,
                f"{nice_field_name} should have 8 characters",
            )
        return v

    @staticmethod
    def parse(input: str) -> Optional["FirmwareHeader"]:
        if not input or len(input) != 32 or not input.startswith("%%"):
            return None
        return FirmwareHeader(
            header_version=input[2:8],
            cloud_version=input[8:14],
            firmware_version=input[14:22],
        )


def remove_header(tmp: Path, firmware: Path) -> Path:
    without_header_file = tmp / f"{firmware.stem}.no_header{firmware.suffix}"

    with firmware.open("rb") as original_file:
        original_file.seek(32)
        with without_header_file.open("wb") as new_file:
            shutil.copyfileobj(original_file, new_file)
            return without_header_file


def process_firmware_file(
    tmp: Path, state: CameraState
) -> tuple[Path, FirmwareHeader | None]:
    if (
        not state.firmware_file.value
        or not state.firmware_file.value.is_file()
        or not state.firmware_file.value.exists()
    ):
        return (Path(), None)
    firmware: Path = state.firmware_file.value
    with firmware.open("rb") as file:
        try:
            first_32_header_chars = file.read(32).decode("utf-8")
            header = FirmwareHeader.parse(first_32_header_chars)
            if header:
                tmp_firmware = remove_header(tmp, firmware)
                return (tmp_firmware, header)
        except UnicodeDecodeError:
            pass
    tmp_firmware = tmp / firmware.name
    shutil.copy(state.firmware_file.value, tmp_firmware)
    return (tmp_firmware, None)


def validate_firmware_file(
    file_path: Path,
    file_type: OTAUpdateModule,
    version: str,
    current_cfg: Optional[DeviceConfiguration],
    header: FirmwareHeader | None = None,
) -> FirmwareValidationStatus:

    if not file_path.is_file():
        raise UserException(
            ErrorCodes.EXTERNAL_FIRMWARE_FILE_NOT_EXISTS,
            "Firmware file does not exist!",
        )

    if current_cfg is None:
        logger.debug("DeviceConfiguration is None.")
        return FirmwareValidationStatus.INVALID

    if not version or len(version) > 31:
        logger.debug(f"Firmware version {version} is invalid")
        return FirmwareValidationStatus.INVALID

    if file_type == OTAUpdateModule.APFW:
        if file_path.suffix != FirmwareExtension.APPLICATION_FW:
            raise UserException(
                ErrorCodes.EXTERNAL_FIRMWARE_INVALID_APPLICATION_FIRMWARE,
                "Invalid Application Firmware!",
            )

        if current_cfg.Version.ApFwVersion == version:
            logger.debug(
                "Received firmware is the same as the one currently installed in the device."
            )
            return FirmwareValidationStatus.SAME_FIRMWARE

        if not header and version.endswith("PD"):
            logger.debug("Reject versions ending in PD.")
            return FirmwareValidationStatus.INVALID
    else:
        if file_path.suffix != FirmwareExtension.SENSOR_FW:
            raise UserException(
                ErrorCodes.EXTERNAL_FIRMWARE_INVALID_SENSOR_FIRMWARE,
                "Invalid Sensor Firmware!",
            )

        if current_cfg.Version.SensorFwVersion == version:
            logger.debug(
                "Received firmware is the same as the one currently installed in the device."
            )
            return FirmwareValidationStatus.SAME_FIRMWARE

    return FirmwareValidationStatus.VALID


def progress_update_checkpoint(
    update_status: str | None,
    is_changed: bool,
    error_notify: Callable,
) -> bool:
    """
    :return: True if break OTA
    """
    # Force change of status from before OTA
    if not is_changed:
        return False

    if update_status == OTAUpdateStatus.FAILED:
        error_notify("Task failed deployment")
        return True

    if update_status == OTAUpdateStatus.DONE:
        return True

    return False


def get_ota_update_status(state: CameraState) -> str | None:
    if state.device_config.value:
        device_config: DeviceConfiguration = state.device_config.value
        return device_config.OTA.UpdateStatus
    return None


async def update_firmware_task(
    state: CameraState,
    error_notify: Callable,
    use_configured_port: bool = False,
) -> None:
    assert state.firmware_file.value
    assert state.firmware_file_type.value
    assert state.firmware_file_version.value

    with TemporaryDirectory(prefix="lc_update_") as temporary_dir:
        tmp_dir = Path(temporary_dir)
        tmp_firmware, firmware_header = process_firmware_file(tmp_dir, state)
        if firmware_header:
            state.firmware_file_version.value = firmware_header.firmware_version

        validation_status: FirmwareValidationStatus = FirmwareValidationStatus.INVALID
        try:
            validation_status = validate_firmware_file(
                state.firmware_file.value,
                state.firmware_file_type.value,
                state.firmware_file_version.value,
                state.device_config.value,
                firmware_header,
            )
        except UserException as e:
            error_notify(str(e))
            return
        if validation_status == FirmwareValidationStatus.INVALID:
            error_notify("Firmware validation failed.")
            return
        elif validation_status == FirmwareValidationStatus.SAME_FIRMWARE:
            logger.debug("No action needed. Firmware update operation is finished.")
            error_notify("Already same Firmware version is available")
            return

        config = config_obj.get_config()
        assert state.mqtt_port.value
        config_device = config_obj.get_device_config(state.mqtt_port.value)
        schema = OnWireProtocol.from_iot_spec(config.evp.iot_platform)
        ephemeral_agent = Agent(
            config_device.mqtt.host, config_device.mqtt.port, schema
        )
        webserver_port = config_device.webserver.port if use_configured_port else 0
        ip_addr = get_webserver_ip(config_device)

        logger.debug("Firmware update operation will start.")
        timeout_secs = 60 * 4
        with trio.move_on_after(timeout_secs) as timeout_scope:
            async with (
                ephemeral_agent.mqtt_scope(
                    [MQTTTopics.ATTRIBUTES_REQ.value, MQTTTopics.ATTRIBUTES.value]
                ),
                AsyncWebserver(tmp_dir, webserver_port, None, True) as serve,
            ):
                # Fill config spec
                update_spec = configuration_spec(
                    state.firmware_file_type.value,
                    tmp_firmware,
                    tmp_dir,
                    serve.port,
                    ip_addr,
                )
                # Use version specified by the user
                update_spec.OTA.DesiredVersion = state.firmware_file_version.value

                payload = update_spec.model_dump_json()
                logger.debug(f"Update spec is: {payload}")

                original_update_status = get_ota_update_status(state)
                is_changed = False

                logger.debug(f"Status before OTA is: {original_update_status}")

                await ephemeral_agent.configure(
                    "backdoor-EA_Main", "placeholder", payload
                )
                while True:
                    """
                    This loop assumes that `state` is updated by a main
                    loop that reacts to reports from the camera, such as
                    `MQTTMixin.mqtt_setup`.
                    """
                    await state.ota_event()
                    timeout_scope.deadline += timeout_secs

                    update_status = get_ota_update_status(state)
                    is_changed = is_changed or original_update_status != update_status
                    logger.debug(f"OTA status is {update_status}")
                    if progress_update_checkpoint(
                        update_status, is_changed, error_notify
                    ):
                        logger.debug("Finished updating!")
                        break

        if timeout_scope.cancelled_caught:
            error_notify("Firmware update timed out!")
            logger.warning("Timeout while updating firmware.")

        logger.debug("Firmware update operation is finished.")
