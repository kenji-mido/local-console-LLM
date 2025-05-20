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

from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.deploy_config import DeployConfig
from local_console.core.deploy_config import DeployConfigIn
from local_console.core.deploy_config import EdgeAppIn
from local_console.core.edge_apps import EdgeApp
from local_console.core.edge_apps import PostEdgeAppsRequestIn
from local_console.core.files.files_validators import ValidableFileInfo
from local_console.core.files.inference import Inference
from local_console.core.files.inference import InferenceDetail
from local_console.core.files.inference import InferenceWithSource
from local_console.core.files.values import FileInfo
from local_console.core.files.values import FileType
from local_console.core.files.values import ZipInfo
from local_console.core.firmwares import Firmware
from local_console.core.firmwares import FirmwareIn
from local_console.core.models import Model
from local_console.core.models import PostModelsIn
from local_console.fastapi.routes.firmwares import FirmwareInfoDTO
from local_console.fastapi.routes.firmwares import FirmwareManifestDTO
from local_console.fastapi.routes.interfaces.dto import NetworkInterface
from local_console.fastapi.routes.interfaces.dto import NetworkStatus
from local_console.utils.timing import as_timestamp
from local_console.utils.validation.aot import AOT_HEADER
from local_console.utils.validation.imx500 import IMX500_MODEL_PKG_HEADER


def model_content(body: bytes = b"Content of the body") -> bytes:
    return bytes(IMX500_MODEL_PKG_HEADER) + body


def app_content(body: bytes = b"Content of the body") -> bytes:
    return bytes(AOT_HEADER) + body


class FileInfoSampler:
    def __init__(
        self,
        id: str = "1",
        path: Path = Path("/not/existing/file"),
        type: FileType = FileType.APP,
    ) -> None:
        self.id = id
        self.path = path
        self.type = type

    def sample(self) -> FileInfo:
        return FileInfo(id=self.id, path=self.path, type=self.type)


class ZipInfoSampler(FileInfoSampler):
    def __init__(
        self,
        id: str = "1",
        path: Path = Path("/extracted/zip"),
        type: FileType = FileType.APP,
        list_files: list[str] = ["manifest.json", "firmware.bin"],
    ) -> None:
        super().__init__(id, path, type)
        self.files = list_files

    def sample(self) -> ZipInfo:
        return ZipInfo(
            id=self.id, path=self.path, type=self.type, list_files=self.files
        )


class ValidableFileInfoSampler(FileInfoSampler):
    def __init__(
        self,
        id: str = "1",
        path: Path = Path("/not/existing/file"),
        type: FileType = FileType.APP,
        content: bytes = app_content(),
    ) -> None:
        super().__init__(id, path, type)
        self.content = content

    def sample(self) -> ValidableFileInfo:
        return ValidableFileInfo(
            id=self.id, path=self.path, type=self.type, content=self.content
        )


class FirmwareInfoDTOSampler:
    def __init__(
        self,
        path: Path = Path("firmware/file.bin"),
        firmware_id: str = "firmware_id",
        firmware_type: str = "SensorFw",
        internal_type: OTAUpdateModule = OTAUpdateModule.SENSORFW,
        firmware_version: str = "1.0",
        description: str | None = "description",
        ins_id: str | None = "ins_id",
        ins_date: str | None = "ins_date",
        upd_id: str | None = "upd_id",
        upd_date: str | None = "upd_date",
        target_device_types: list[str] | None = [],
        manifest: FirmwareManifestDTO | None = None,
    ) -> None:
        self.path = path
        self.firmware_id = firmware_id
        self.firmware_type = firmware_type
        self.internal_type = internal_type
        self.firmware_version = firmware_version
        self.description = description
        self.ins_id = ins_id
        self.ins_date = ins_date
        self.upd_id = upd_id
        self.upd_date = upd_date
        self.target_device_types = target_device_types
        self.manifest = manifest

    def sample(self) -> FirmwareInfoDTO:
        return FirmwareInfoDTO(
            path=self.path,
            firmware_id=self.firmware_id,
            firmware_type=self.firmware_type,
            internal_type=self.internal_type,
            firmware_version=self.firmware_version,
            description=self.description,
            ins_id=self.ins_id,
            ins_date=self.ins_date,
            upd_id=self.upd_id,
            upd_date=self.upd_date,
            target_device_types=self.target_device_types,
            manifest=self.manifest,
        )


class FirmwareInSampler:
    def __init__(
        self,
        firmware_type: OTAUpdateModule = OTAUpdateModule.SENSORFW,
        description: str | None = "Sample description",
        file_id: str = "file_id",
        version: str = "v0.1",
    ) -> None:
        self.firmware_type = firmware_type
        self.description = description
        self.file_id = file_id
        self.version = version

    def sample(self) -> FirmwareIn:
        return FirmwareIn(
            firmware_type=self.firmware_type,
            description=self.description,
            file_id=self.file_id,
            version=self.version,
        )


class FirmwareSampler:
    def __init__(
        self,
        firmware_id: str = "firmware_id",
        info: FirmwareInSampler = FirmwareInSampler(),
        file: FileInfoSampler = FileInfoSampler(),
    ) -> None:
        self.firmware_id = firmware_id
        self.info = info
        self.file = file

    def sample(self) -> Firmware:
        return Firmware(
            firmware_id=self.firmware_id,
            file=self.file.sample(),
            info=self.info.sample(),
        )


class PostModelsInSampler:
    def __init__(
        self, model_id: str = "model_id", model_file_id: str = "model_file_id"
    ) -> None:
        self.model_id = model_id
        self.model_file_id = model_file_id

    def sample(self) -> PostModelsIn:
        return PostModelsIn(model_id=self.model_id, model_file_id=self.model_file_id)


class ModelSampler:
    def __init__(
        self,
        file: FileInfoSampler = FileInfoSampler(),
        info: PostModelsInSampler = PostModelsInSampler(),
    ) -> None:
        self.file = file
        self.info = info

    def sample(self) -> Model:
        return Model(file=self.file.sample(), info=self.info.sample())


class PostEdgeAppsRequestInSampler:
    def __init__(self, edge_app_id: str = "app_id", app_name: str = "app_name") -> None:
        self.edge_app_id = edge_app_id
        self.app_name = app_name

    def sample(self) -> PostEdgeAppsRequestIn:
        return PostEdgeAppsRequestIn(
            edge_app_package_id=self.edge_app_id, app_name=self.app_name, description=""
        )


class EdgeAppSampler:
    def __init__(
        self,
        file: FileInfoSampler = FileInfoSampler(),
        info: PostEdgeAppsRequestInSampler = PostEdgeAppsRequestInSampler(),
    ) -> None:
        self.file = file
        self.info = info

    def sample(self) -> EdgeApp:
        return EdgeApp(file=self.file.sample(), info=self.info.sample())


class EdgeAppConfigInSampler:
    def __init__(self, edge_app_id: str = "edge_app_id", version: str = "version"):
        self.edge_app_id = edge_app_id
        self.version = version

    def sample(self) -> EdgeAppIn:
        return EdgeAppIn(edge_app_id=self.edge_app_id, version=self.version)


class DeployConfigInSampler:
    def __init__(
        self,
        config_id: str = "config_id",
        fw_ids: list[str] = ["fw_id"],
        edge_app_ids: list[str] = ["app_id"],
        model_ids: list[str] = ["model_id"],
    ) -> None:
        self.config_id = config_id
        self.fw_ids = fw_ids
        self.model_ids = model_ids
        self.edge_app_ids = edge_app_ids

    def sample(self) -> DeployConfigIn:
        return DeployConfigIn(
            config_id=self.config_id,
            fw_ids=self.fw_ids,
            edge_apps=[
                EdgeAppConfigInSampler(edge_app_id).sample()
                for edge_app_id in self.edge_app_ids
            ],
            model_ids=self.model_ids,
        )


class DeployConfigSampler:
    def __init__(
        self,
        config_id: str = "config_id",
        firmware: FirmwareSampler | None = FirmwareSampler(),
        app: EdgeAppSampler = EdgeAppSampler(),
        num_apps: int = 1,
        model: ModelSampler = ModelSampler(),
        num_models: int = 1,
    ) -> None:
        self.config_id = config_id
        self.firmware = firmware
        self.app = app
        self.num_apps = num_apps
        self.model = model
        self.num_models = num_models

    def sample(self) -> DeployConfig:
        return DeployConfig(
            config_id=self.config_id,
            firmwares=[self.firmware.sample()] if self.firmware else [],
            edge_apps=[self.app.sample() for _ in range(self.num_apps)],
            models=[self.model.sample() for _ in range(self.num_models)],
        )


class InferenceDetailSampler:
    def __init__(
        self,
        t: str = as_timestamp(),
        o: str = "aGVsbG8=",
    ) -> None:
        self.t = t
        self.o = o

    def sample(self) -> InferenceDetail:
        return InferenceDetail(t=self.t, o=self.o)


class InferenceSampler:
    def __init__(
        self,
        device_id: str = "device_id",
        model_id: str = "model_id",
        image: bool = True,
        inferences: list[InferenceDetailSampler] = [InferenceDetailSampler()],
    ) -> None:
        self.device_id = device_id
        self.model_id = model_id
        self.image = image
        self.inferences = inferences

    def sample(self) -> Inference:
        return Inference(
            device_id=self.device_id,
            model_id=self.model_id,
            image=self.image,
            inferences=[i.sample() for i in self.inferences],
        )


class InferenceWithSourceSampler:
    def __init__(
        self,
        path: Path = Path(f"/base/path/{as_timestamp()}.txt"),
        inference: InferenceSampler = InferenceSampler(),
    ) -> None:
        self.path = path
        self.inference = inference

    def sample(self) -> InferenceWithSource:
        return InferenceWithSourceSampler(
            path=self.path, inference=self.inference.sample()
        )


class NetworkInterfaceSampler:
    def __init__(
        self,
        name: str = "name",
        ip: str = "ip",
        status: NetworkStatus = NetworkStatus.UP,
    ) -> None:
        self.name = name
        self.ip = ip
        self.status = status

    def sample(self) -> NetworkInterface:
        return NetworkInterface(
            name=self.name,
            ip=self.ip,
            status=self.status.value,
        )
