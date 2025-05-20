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
import json

from pydantic import BaseModel


class AIModel(BaseModel):
    version: str
    hash: str
    update_date: str


class Chip(BaseModel):
    name: str
    id: str
    hardware_version: str
    temperature: int
    loader_version: str
    loader_hash: str
    update_date_loader: str
    firmware_version: str
    firmware_hash: str
    update_date_firmware: str
    ai_models: list[AIModel]


class DeviceInfo(BaseModel):
    device_manifest: str
    chips: list[Chip]


class DecodedDeviceManifest(BaseModel):
    AITRIOSCertUUID: str

    @classmethod
    def from_device_manifest(cls, value: str) -> "DecodedDeviceManifest":
        parts = value.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT token format")

        # JWT uses url-safe base64 encoding without padding
        payload_b64 = parts[1]
        # fix padding
        padding = "=" * (-len(payload_b64) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
        payload = json.loads(payload_bytes.decode("utf-8"))
        return cls(**payload)
