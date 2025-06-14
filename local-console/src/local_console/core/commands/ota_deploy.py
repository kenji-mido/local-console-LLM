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
from base64 import b64encode
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.enums import AiModelExtension
from local_console.core.schemas.edge_cloud_if_v1 import DnnOta
from local_console.core.schemas.edge_cloud_if_v1 import DnnOtaBody


def get_package_hash(package_file: Path) -> str:
    digest = hashes.Hash(hashes.SHA256())
    digest.update(package_file.read_bytes())
    return b64encode(digest.finalize()).decode()


def reverse_bytes_4(value: bytes) -> bytes:
    assert len(value) % 4 == 0
    return b"".join([value[i * 4 : i * 4 + 4][::-1] for i in range(0, len(value) // 4)])


def get_package_version_pkg(package_file: Path) -> bytes:
    return package_file.read_bytes()[0x30:0x40]


def get_package_version_rpk(package_file: Path) -> bytes:
    return reverse_bytes_4(get_package_version_pkg(package_file))


def get_package_version(package_file: Path) -> str:
    package_version = (
        get_package_version_rpk(package_file)
        if AiModelExtension.RPK.as_suffix == package_file.suffix
        else get_package_version_pkg(package_file)
    )
    return package_version.decode()


def get_network_id(package_file: Path) -> str:
    ver_bytes = get_package_version(package_file)
    return ver_bytes[6 : 6 + 6]


def configuration_spec(
    ota_type: OTAUpdateModule,
    package_file: Path,
    url: str,
) -> DnnOta:
    file_hash = get_package_hash(package_file)
    # version for ApFw and SensorFw are specified by the user
    version_str = (
        get_package_version(package_file)
        if ota_type == OTAUpdateModule.DNNMODEL
        else ""
    )
    return DnnOta(
        OTA=DnnOtaBody(
            UpdateModule=ota_type,
            DesiredVersion=version_str,
            PackageUri=url,
            HashValue=file_hash,
        )
    )


def get_network_ids(dnn_model_version: list[str]) -> list[str]:
    return [desired_version[6 : 6 + 6] for desired_version in dnn_model_version]


def get_apfw_version_string(fw_binary: bytes) -> str:
    # Note that the following only holds if the binary is UNENCRYPTED
    offset = fw_binary.index(b"PROJECT_NAME")
    if offset < 0:
        raise ValueError("Cannot find esp_app_desc_nx_adp_t struct in firmware")
    # Now, look the version string up, as it is located
    # contiguously before the `PROJECT_NAME` string,
    # with some surrounding zero padding.
    while offset > 0 and fw_binary[offset - 1] == 0:
        offset -= 1
    if fw_binary[offset - 1] == 0:
        raise ValueError("Could not locate the end of version string")
    end = offset

    while offset > 0 and fw_binary[offset - 1] != 0:
        offset -= 1
    if fw_binary[offset - 1] != 0:
        raise ValueError("Could not locate the start of version string")
    start = offset

    return fw_binary[start:end].decode()
