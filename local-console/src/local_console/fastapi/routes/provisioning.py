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
import base64
from datetime import datetime
from datetime import timedelta
from io import BytesIO

from fastapi import APIRouter
from fastapi import Depends
from fastapi import status
from local_console.core.camera.qr.schema import QRInfo
from local_console.fastapi.dependencies.devices import InjectDeviceServices
from pydantic import BaseModel

router = APIRouter(prefix="/provisioning", tags=["Project"])


class QrCodeResponse(BaseModel):
    result: str = "SUCCESS"
    contents: str
    expiration_date: str


@router.get(
    "/qrcode",
    status_code=status.HTTP_200_OK,
    summary="Generate a QR to add a device and start a MQTT server on the specified port",
)
async def get_qr_code_for_provisioning_func(
    device_service: InjectDeviceServices,
    dto: QRInfo = Depends(),
) -> QrCodeResponse:

    qr = device_service.qr.generate(dto)

    img = qr.make_image(fill="black", back_color="white")

    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    # Encode the image to base64
    contents = base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")
    expiration_date = datetime.now() + timedelta(days=1)

    return QrCodeResponse(
        contents=contents, expiration_date=expiration_date.astimezone().isoformat()
    )
