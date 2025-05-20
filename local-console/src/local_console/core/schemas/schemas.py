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
import logging
from pathlib import Path
from typing import Annotated
from typing import Any
from typing import NewType
from typing import Optional

from local_console.core.camera.enums import ApplicationType
from local_console.core.camera.enums import UnitScale
from local_console.core.camera.qr.schema import QRInfo
from local_console.utils.enums import StrEnum
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

logger = logging.getLogger(__name__)


IPAddress = Field(pattern=r"^[\w\d_][\w.-]*$")

IPPortNumber = Field(ge=0, le=65535)

DeviceID = NewType("DeviceID", Annotated[int, Field(gt=0)])
# FIXME: Doing `DeviceID(str)` does not cast it to integer


class Libraries(BaseModel):
    libraries: list[Optional[str]]


class InstanceSpec(BaseModel):
    moduleId: str
    subscribe: dict[str, str] = {}
    publish: dict[str, str] = {}


class Module(BaseModel):
    entryPoint: str
    moduleImpl: str
    downloadUrl: str
    hash: str


class Topics(BaseModel):
    type: str
    topic: str


class Deployment(BaseModel):
    deploymentId: str
    instanceSpecs: dict[str, InstanceSpec]
    modules: dict[str, Module]
    publishTopics: dict[str, Topics]
    subscribeTopics: dict[str, Topics]


class DeploymentManifest(BaseModel):
    deployment: Deployment

    def render_for_evp1(self) -> str:
        # The actual manifest, which is the value of the "deployment" key, is stringified.
        # Also, the fields differ and EVP1 has two mandatory fields in the instanceSpecs.
        body = self.deployment
        difference_hack = body.model_dump()
        for instance in difference_hack["instanceSpecs"].values():
            instance.update({"version": 1, "entryPoint": "main"})
        as_json = json.dumps(difference_hack)
        return json.dumps({"deployment": as_json})

    def render_for_evp2(self) -> str:
        # A direct JSON serialization
        return json.dumps(self.model_dump())


class DesiredDeviceConfig(BaseModel):
    reportStatusIntervalMax: Annotated[int, Field(ge=0, le=65535)]
    reportStatusIntervalMin: Annotated[int, Field(ge=0, le=65535)]


class OnWireProtocol(StrEnum):
    EVP1 = "EVP1"
    EVP2 = "EVP2"

    @classmethod
    def _missing_(cls, value: object) -> Any:
        # Normalize the value in the case of EVP2-TB and EVP2-C8Y
        if isinstance(value, str) and value.startswith("EVP2"):
            return cls.EVP2
        return None  # Let the default error be raised if no match is found

    @property
    def for_agent_environ(self) -> str:
        if self == self.EVP1:
            return "evp1"

        return "tb"


class DeviceType(StrEnum):
    RPi = "Raspberry Pi"
    T3P_SZP = "SZP123S-001"
    T3P_CSV = "CSV26"
    T3P_AIH = "AIH-IVRW2"
    UNKNOWN = "Unknown"

    @classmethod
    def from_value(cls, value: str) -> "DeviceType":
        manufacture_id = value[4:8]
        model_id = value[8:12]
        if manufacture_id in ["8001", "0001"] and model_id != "0006":
            return cls.T3P_SZP
        elif manufacture_id in ["8007", "0001"]:
            return cls.T3P_AIH
        elif manufacture_id == "8005":
            return cls.T3P_CSV
        return cls.UNKNOWN


class DeviceListItem(BaseModel):
    name: str
    port: Annotated[int, IPPortNumber]
    id: DeviceID
    onwire_schema: OnWireProtocol


class MQTTParams(BaseModel, validate_assignment=True):
    host: str = IPAddress
    port: int = IPPortNumber
    device_id: Optional[Annotated[str, Field(pattern=r"^[_a-zA-Z][\w_.-]*$")]]


class WebserverParams(BaseModel):
    host: str = IPAddress
    port: int = IPPortNumber


DeviceName = Field(pattern=r"^[A-Za-z0-9\-_.]+$", min_length=1, max_length=255)


class Persist(BaseModel):
    module_file: Path | None = None
    ai_model_file: Path | None = None
    device_dir_path: Path | None = None
    size: Optional[Annotated[int, Field(gt=0)]] = None
    unit: UnitScale | None = None
    vapp_type: ApplicationType | None = ApplicationType.IMAGE
    vapp_schema_file: str | None = None
    vapp_config_file: str | None = None
    vapp_labels_file: str | None = None
    auto_deletion: bool = False

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("unit", mode="before")
    @classmethod
    def unit_scale_validator(cls, v: str) -> UnitScale | None:
        if not v:
            return None
        return UnitScale.from_value(v)


class DeviceConnection(BaseModel):
    mqtt: MQTTParams
    name: str = DeviceName
    id: DeviceID
    onwire_schema: OnWireProtocol
    persist: Persist = Persist()
    qr: QRInfo | None = None

    model_config = ConfigDict(validate_assignment=True)


class ModelDeploymentConfig(BaseModel):
    undeploy_timeout: float = 200.0
    deploy_timeout: float = 200.0


class DeploymentConfig(BaseModel):
    model: ModelDeploymentConfig = ModelDeploymentConfig()


class LocalConsoleConfig(BaseModel):
    deployment: DeploymentConfig = DeploymentConfig()
    webserver: WebserverParams


class GlobalConfiguration(BaseModel):
    devices: list[DeviceConnection]
    config: LocalConsoleConfig

    model_config = ConfigDict(validate_assignment=True)
