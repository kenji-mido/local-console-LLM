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
"""
Edge Cloud IF v1 schemas. Properties not included here are ignored. For example, PQ settings.
"""
from local_console.utils.schemas import ListModel
from pydantic import BaseModel
from pydantic import Field


class Hardware(BaseModel):
    Sensor: str
    SensorId: str
    KG: str
    ApplicationProcessor: str
    LedOn: bool


class DnnModelVersion(ListModel):
    root: list[str]


class CameraSetupFileVersionType(BaseModel):
    ColorMatrixStd: str | None = None
    ColorMatrixCustom: str | None = None
    GammaStd: str | None = None
    GammaCustom: str | None = None
    LSCISPStd: str | None = None
    LSCISPCustom: str | None = None
    LSCRawStd: str | None = None
    LSCRawCustom: str | None = None
    PreWBStd: str | None = None
    PreWBCustom: str | None = None
    DewarpStd: str | None = None
    DewarpCustom: str | None = None


class Version(BaseModel):
    SensorFwVersion: str
    SensorLoaderVersion: str | None = None
    DnnModelVersion: DnnModelVersion
    ApFwVersion: str
    ApLoaderVersion: str | None = None
    CameraSetupFileVersion: CameraSetupFileVersionType | None = None


class Status(BaseModel):
    Sensor: str
    ApplicationProcessor: str
    SensorTemperature: int | None = None
    HoursMeter: int | None = None


class OTA(BaseModel):
    UpdateModule: str | None = None
    ReplaceNetworkID: str | None = None
    DeleteNetworkID: str | None = None
    PackageUri: str | None = None
    DesiredVersion: str | None = None
    HashValue: str | None = None
    SensorFwLastUpdatedDate: str
    SensorLoaderLastUpdatedDate: str
    DnnModelLastUpdatedDate: list[str]
    ApFwLastUpdatedDate: str
    CameraSetupFunction: str | None = None
    CameraSetupMode: str | None = None
    UpdateProgress: int
    UpdateStatus: str


class ImageType(BaseModel):
    FrameRate: int | None = None
    DriveMode: int | None = None


class ExposureType(BaseModel):
    ExposureMode: str | None = None
    ExposureMaxExposureTime: int | None = None
    ExposureMinExposureTime: int | None = None
    ExposureMaxGain: int | None = None
    AESpeed: int | None = None
    ExposureCompensation: int | None = None
    ExposureTime: int | None = None
    ExposureGain: int | None = None
    FlickerReduction: int | None = None


class WhiteBalanceType(BaseModel):
    WhiteBalanceMode: str | None = None
    WhiteBalancePreset: int | None = None
    WhiteBalanceSpeed: int | None = None


class AdjustmentType(BaseModel):
    ColorMatrix: str | None = None
    Gamma: str | None = None
    LSCISP: str | None = Field(None, alias="LSC-ISP")
    LSCRaw: str | None = Field(None, alias="LSC-Raw")
    PreWB: str | None = None
    Dewarp: str | None = None


class RotationType(BaseModel):
    RotAngle: int | None = None


class DirectionType(BaseModel):
    Vertical: str | None = None
    Horizontal: str | None = None


class Permission(BaseModel):
    FactoryReset: bool


class Network(BaseModel):
    ProxyURL: str
    ProxyPort: int
    ProxyUserName: str
    IPAddress: str
    SubnetMask: str
    Gateway: str
    DNS: str
    NTP: str


class BatteryType(BaseModel):
    Voltage: int | None = None
    InUse: str | None = None
    Alarm: bool | None = None


class IntervalType(BaseModel):
    ConfigInterval: int | None = None
    CaptureInterval: int | None = None
    BaseTime: str | None = None
    UploadCount: int | None = None


class UploadInferenceParameterType(BaseModel):
    UploadMethodIR: str | None = None
    StorageNameIR: str | None = None
    StorageSubDirectoryPathIR: str | None = None
    PPLParameter: str | None = None
    CropHOffset: int | None = None
    CropVOffset: int | None = None
    CropHSize: int | None = None
    CropVSize: int | None = None
    NetworkId: str | None = None


class PeriodicParameterType(BaseModel):
    NetworkParameter: str | None = None
    PrimaryInterval: IntervalType | None = None
    SecondaryInterval: IntervalType | None = None
    UploadInferenceParameter: UploadInferenceParameterType | None = None


class FWOperationType(BaseModel):
    OperatingMode: str | None = None
    ErrorHandling: str | None = None
    PeriodicParameter: PeriodicParameterType | None = None


class DeviceConfiguration(BaseModel):
    Hardware: Hardware
    Version: Version
    Status: Status
    OTA: OTA
    Image: ImageType | None = None
    Exposure: ExposureType | None = None
    WhiteBalance: WhiteBalanceType | None = None
    Adjustment: AdjustmentType | None = None
    Rotation: RotationType | None = None
    Direction: DirectionType | None = None
    Permission: Permission
    Network: None | Network
    Battery: BatteryType | None = None
    FWOperation: FWOperationType | None = None


class DnnOtaBody(BaseModel):
    UpdateModule: str = Field(default="DnnModel")
    DesiredVersion: str
    PackageUri: str
    HashValue: str


class DnnOta(BaseModel):
    OTA: DnnOtaBody


class DnnDeleteBody(BaseModel):
    UpdateModule: str = Field(default="DnnModel")
    DeleteNetworkID: str


class DnnDelete(BaseModel):
    OTA: DnnDeleteBody


class SetFactoryReset(BaseModel):
    Permission: Permission


class StartUploadInferenceData(BaseModel):
    Mode: int = 1
    UploadMethod: str = "HttpStorage"
    StorageName: str
    StorageSubDirectoryPath: str
    UploadMethodIR: str = "HttpStorage"
    StorageNameIR: str
    UploadInterval: int = 30
    StorageSubDirectoryPathIR: str
    CropHOffset: int
    CropVOffset: int
    CropHSize: int
    CropVSize: int
