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
from typing import Callable
from typing import Optional

from local_console.core.camera.enums import FirmwareExtension
from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.camera.enums import OTAUpdateStatus
from local_console.core.camera.schemas import PropertiesReport
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes
from pydantic import BaseModel
from pydantic import field_validator
from pydantic import ValidationInfo

logger = logging.getLogger(__name__)


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


class FirmwareInfo(BaseModel):
    path: Path
    hash: str
    version: str
    is_valid: bool
    type: OTAUpdateModule


def remove_header(tmp: Path, firmware: Path) -> Path:
    without_header_file = tmp / f"{firmware.stem}.no_header{firmware.suffix}"

    with firmware.open("rb") as original_file:
        original_file.seek(32)
        with without_header_file.open("wb") as new_file:
            shutil.copyfileobj(original_file, new_file)
            return without_header_file


def process_firmware_file(
    tmp: Path, firmware_info: FirmwareInfo
) -> tuple[Path, FirmwareHeader | None]:
    if not firmware_info.path.is_file() or not firmware_info.path.exists():
        return Path(), None
    with firmware_info.path.open("rb") as file:
        try:
            first_32_header_chars = file.read(32).decode("utf-8")
            header = FirmwareHeader.parse(first_32_header_chars)
            if header:
                tmp_firmware = remove_header(tmp, firmware_info.path)
                return (tmp_firmware, header)
        except UnicodeDecodeError:
            pass
    tmp_firmware = tmp / firmware_info.path.name
    shutil.copy(firmware_info.path, tmp_firmware)
    return tmp_firmware, None


def validate_firmware_file(
    file_path: Path,
    file_type: OTAUpdateModule,
    version: str,
    current_cfg: PropertiesReport,
    header: FirmwareHeader | None = None,
) -> FirmwareValidationStatus:

    if not file_path.is_file():
        raise UserException(
            ErrorCodes.EXTERNAL_FIRMWARE_FILE_NOT_EXISTS,
            "Firmware file does not exist!",
        )

    if not version or len(version) > 31:
        logger.debug(f"Firmware version {version} is invalid")
        return FirmwareValidationStatus.INVALID

    if file_type == OTAUpdateModule.APFW:
        if file_path.suffix != FirmwareExtension.APPLICATION_FW:
            raise UserException(
                ErrorCodes.EXTERNAL_FIRMWARE_INVALID_APPLICATION_FIRMWARE,
                "Invalid Application Firmware!",
            )

        if current_cfg.cam_fw_version == version:
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

        if current_cfg.sensor_fw_version == version:
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
