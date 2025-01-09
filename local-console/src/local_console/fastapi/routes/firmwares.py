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
from typing import Annotated
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Request
from local_console.core.firmwares import Firmware
from local_console.core.firmwares import FirmwareIn
from local_console.core.firmwares import FirmwareManager
from local_console.fastapi.dependencies.commons import InjectFilesManager
from local_console.fastapi.pagination import FirmwaresPaginator
from pydantic import BaseModel

router = APIRouter(prefix="/firmwares", tags=["Firmware"])


class FirmwareManifestSWDTO(BaseModel):
    file_name: str
    version: str
    type: str


class FirmwareManifestDTO(BaseModel):
    package_version: str
    target_device_types: Optional[list[str]] = None
    sw_list: list[FirmwareManifestSWDTO]


class FirmwareInfoDTO(BaseModel):
    firmware_id: str
    firmware_type: str | None = None
    firmware_version: str | None = None
    description: str | None = None
    ins_id: str | None = None
    ins_date: str | None = None
    upd_id: str | None = None
    upd_date: str | None = None
    target_device_types: list[str] | None = None
    manifest: FirmwareManifestDTO | None = None


class FirmwareOutDTO(BaseModel):
    continuation_token: None | str
    firmwares: list[FirmwareInfoDTO]


class FirmwareRequestOutDTO(BaseModel):
    result: str = "SUCCESS"


def firmware_manager(
    request: Request, file_manager: InjectFilesManager
) -> FirmwareManager:
    app = request.app
    if not hasattr(app.state, "firmware_manager"):
        firmware_manager = FirmwareManager(file_manager)
        app.state.firmware_manager = firmware_manager
    assert isinstance(app.state.firmware_manager, FirmwareManager)
    return app.state.firmware_manager


InjectFirmwareManager = Annotated[FirmwareManager, Depends(firmware_manager)]


@router.get("")
async def get_firmwares(
    firmware_manager: InjectFirmwareManager,
    limit: int = Query(
        50,
        ge=0,
        le=256,
        description="Number of Edge Apps to fetch. Value range: 0 to 256",
    ),
    starting_after: str | None = Query(
        None, description="A token to use in pagination."
    ),
) -> FirmwareOutDTO:
    list_all_firmwares: list[Firmware] = firmware_manager.get_all()
    list_filtered_firmwares, new_continuation_token = FirmwaresPaginator().paginate(
        list_all_firmwares, limit, starting_after
    )

    list_firmware_return: list[FirmwareInfoDTO] = []
    for firmware in list_filtered_firmwares:
        list_firmware_return.append(
            FirmwareInfoDTO(
                firmware_id=firmware.info.file_id,
                firmware_type=firmware.info.firmware_type,
                firmware_version=firmware.info.version,
                description=firmware.info.description,
            )
        )

    return FirmwareOutDTO(
        continuation_token=new_continuation_token,
        firmwares=list_firmware_return,
    )


@router.post("")
async def post_firmwares(
    request: FirmwareIn, firmware_manager: InjectFirmwareManager
) -> FirmwareRequestOutDTO:
    firmware_manager.register(request)
    return FirmwareRequestOutDTO(result="SUCCESS")
