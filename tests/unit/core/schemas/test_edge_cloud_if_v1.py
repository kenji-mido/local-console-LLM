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
import pytest
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration


def test_validate_fields_added_dts_1003():
    payload = """
{
  "Hardware": {
    "Sensor": "IMX500",
    "SensorId": "100A50500A2010072664012000000000",
    "KG": "1",
    "ApplicationProcessor": "ESP32",
    "LedOn": true
  },
  "Version": {
    "SensorFwVersion": "010707",
    "SensorLoaderVersion": "020301",
    "DnnModelVersion": ["0308000000000100"],
    "ApFwVersion": "D52408",
    "CameraSetupFileVersion": {
      "ColorMatrixStd": "123",
      "ColorMatrixCustom": "456",
      "GammaStd": "789",
      "GammaCustom": "098",
      "LSCISPStd": "765",
      "LSCISPCustom": "432",
      "LSCRawStd": "101",
      "LSCRawCustom": "234",
      "PreWBStd": "567",
      "PreWBCustom": "890",
      "DewarpStd": "987",
      "DewarpCustom": "654"
    }
  },
  "Status": {
    "Sensor": "Standby",
    "ApplicationProcessor": "Idle",
    "SensorTemperature": 50,
    "HoursMeter": 10
  },
  "OTA": {
    "UpdateModule": "SensorFw",
    "ReplaceNetworkID": "0308000000000101",
    "DeleteNetworkID": "0308000000000102",
    "PackageUri": "http://no/sample/provided",
    "DesiredVersion": "010707",
    "HashValue": "d9b6c7f0a7eefccf952a8acfc0fee9ef",
    "SensorFwLastUpdatedDate": "20241107085300",
    "SensorLoaderLastUpdatedDate": "20241007085300",
    "DnnModelLastUpdatedDate": ["20241028151808"],
    "ApFwLastUpdatedDate": "20241106085300",
    "CameraSetupFunction": "ColorMatrix",
    "CameraSetupMode": "custom",
    "UpdateProgress": 100,
    "UpdateStatus": "Done"
  },
  "Image": {
    "FrameRate": 2997,
    "DriveMode": 1
  },
  "Exposure": {
    "ExposureMode": "auto",
    "ExposureMaxExposureTime": 20,
    "ExposureMinExposureTime": 33,
    "ExposureMaxGain": 24,
    "AESpeed": 3,
    "ExposureCompensation": 6,
    "ExposureTime": 18,
    "ExposureGain": 1,
    "FlickerReduction": 7
  },
  "WhiteBalance": {
    "WhiteBalanceMode": "auto",
    "WhiteBalancePreset": 0,
    "WhiteBalanceSpeed": 3
  },
  "Adjustment": {
    "ColorMatrix": "std",
    "Gamma": "std",
    "LSC-ISP": "std",
    "LSC-Raw": "std",
    "PreWB": "std",
    "Dewarp": "off"
  },
  "Rotation": {
    "RotAngle": 0
  },
  "Direction": {
    "Vertical": "Normal",
    "Horizontal": "Normal"
  },
  "Network": {
    "ProxyURL": "http://no/sample/provided",
    "ProxyPort": 0,
    "ProxyUserName": "user",
    "IPAddress": "192.168.1.1",
    "SubnetMask": "255.255.0.0",
    "Gateway": "192.168.1.1",
    "DNS": "8.8.8.8",
    "NTP": "pool.ntp.org"
  },
  "Permission": {
    "FactoryReset": true
  }
}
"""
    device_config = DeviceConfiguration.model_validate_json(payload)

    assert device_config.Hardware.LedOn
    assert device_config.Version.CameraSetupFileVersion
    assert device_config.Version.CameraSetupFileVersion.ColorMatrixStd == "123"
    assert device_config.Version.CameraSetupFileVersion.ColorMatrixCustom == "456"
    assert device_config.Version.CameraSetupFileVersion.GammaStd == "789"
    assert device_config.Version.CameraSetupFileVersion.GammaCustom == "098"
    assert device_config.Version.CameraSetupFileVersion.LSCISPStd == "765"
    assert device_config.Version.CameraSetupFileVersion.LSCISPCustom == "432"
    assert device_config.Version.CameraSetupFileVersion.LSCRawStd == "101"
    assert device_config.Version.CameraSetupFileVersion.LSCRawCustom == "234"
    assert device_config.Version.CameraSetupFileVersion.PreWBStd == "567"
    assert device_config.Version.CameraSetupFileVersion.PreWBCustom == "890"
    assert device_config.Version.CameraSetupFileVersion.DewarpStd == "987"
    assert device_config.Version.CameraSetupFileVersion.DewarpCustom == "654"
    assert device_config.Status.SensorTemperature == 50
    assert device_config.Status.HoursMeter == 10
    assert device_config.OTA.UpdateModule == "SensorFw"
    assert device_config.OTA.ReplaceNetworkID == "0308000000000101"
    assert device_config.OTA.DeleteNetworkID == "0308000000000102"
    assert device_config.OTA.PackageUri == "http://no/sample/provided"
    assert device_config.OTA.DesiredVersion == "010707"
    assert device_config.OTA.HashValue == "d9b6c7f0a7eefccf952a8acfc0fee9ef"
    assert device_config.OTA.CameraSetupFunction == "ColorMatrix"
    assert device_config.OTA.CameraSetupMode == "custom"
    assert device_config.Image.FrameRate == 2997
    assert device_config.Image.DriveMode == 1
    assert device_config.Exposure.ExposureMode == "auto"
    assert device_config.Exposure.ExposureMaxExposureTime == 20
    assert device_config.Exposure.ExposureMinExposureTime == 33
    assert device_config.Exposure.ExposureMaxGain == 24
    assert device_config.Exposure.AESpeed == 3
    assert device_config.Exposure.ExposureCompensation == 6
    assert device_config.Exposure.ExposureTime == 18
    assert device_config.Exposure.ExposureGain == 1
    assert device_config.Exposure.FlickerReduction == 7
    assert device_config.WhiteBalance.WhiteBalanceMode == "auto"
    assert device_config.WhiteBalance.WhiteBalancePreset == 0
    assert device_config.WhiteBalance.WhiteBalanceSpeed == 3
    assert device_config.Adjustment.ColorMatrix == "std"
    assert device_config.Adjustment.Gamma == "std"
    assert device_config.Adjustment.LSCISP == "std"
    assert device_config.Adjustment.LSCRaw == "std"
    assert device_config.Adjustment.PreWB == "std"
    assert device_config.Adjustment.Dewarp == "off"
    assert device_config.Rotation.RotAngle == 0
    assert device_config.Direction.Vertical == "Normal"
    assert device_config.Direction.Horizontal == "Normal"


@pytest.mark.parametrize(
    "payload",
    [
        """
{
  "Hardware": {
    "Sensor": "IMX500",
    "SensorId": "100A50500A2010072664012000000000",
    "KG": "1",
    "ApplicationProcessor": "ESP32",
    "LedOn": true
  },
  "Version": {
    "SensorFwVersion": "010707",
    "SensorLoaderVersion": "020301",
    "DnnModelVersion": ["0308000000000100"],
    "ApFwVersion": "D52408"
  },
  "Status": {
    "Sensor": "Standby",
    "ApplicationProcessor": "Idle",
    "SensorTemperature": 50,
    "HoursMeter": 10
  },
  "OTA": {
    "ReplaceNetworkID": null,
    "PackageUri": null,
    "DesiredVersion": null,
    "SensorFwLastUpdatedDate": "20241107085300",
    "SensorLoaderLastUpdatedDate": "20241007085300",
    "DnnModelLastUpdatedDate": ["20241028151808"],
    "ApFwLastUpdatedDate": "20241106085300",
    "CameraSetupFunction": null,
    "CameraSetupMode": null,
    "UpdateProgress": 100,
    "UpdateStatus": "Done"
  },
  "Network": {
    "ProxyURL": "http://no/sample/provided",
    "ProxyPort": 0,
    "ProxyUserName": "user",
    "IPAddress": "192.168.1.1",
    "SubnetMask": "255.255.0.0",
    "Gateway": "192.168.1.1",
    "DNS": "8.8.8.8",
    "NTP": "pool.ntp.org"
  },
  "Permission": {
    "FactoryReset": true
  }
}
""",
        """
{
  "Hardware": {
    "Sensor": "IMX500",
    "SensorId": "100A50500A2010072664012000000000",
    "KG": "1",
    "ApplicationProcessor": "ESP32",
    "LedOn": true
  },
  "Version": {
    "SensorFwVersion": "010707",
    "SensorLoaderVersion": "020301",
    "DnnModelVersion": ["0308000000000100"],
    "ApFwVersion": "D52408",
    "CameraSetupFileVersion": {
      "ColorMatrixCustom": null,
      "GammaCustom": "098",
      "LSCISPStd": null,
      "LSCRawStd": "101",
      "PreWBStd": "567",
      "DewarpStd": "987",
      "DewarpCustom": "654"
    }
  },
  "Status": {
    "Sensor": "Standby",
    "ApplicationProcessor": "Idle",
    "SensorTemperature": 50,
    "HoursMeter": 10
  },
  "OTA": {
    "UpdateModule": null,
    "DeleteNetworkID": null,
    "HashValue": null,
    "SensorFwLastUpdatedDate": "20241107085300",
    "SensorLoaderLastUpdatedDate": "20241007085300",
    "DnnModelLastUpdatedDate": ["20241028151808"],
    "ApFwLastUpdatedDate": "20241106085300",
    "UpdateProgress": 100,
    "UpdateStatus": "Done"
  },
  "Image": {
    "FrameRate": null
  },
  "Exposure": {
    "ExposureMode": null,
    "FlickerReduction": null
  },
  "WhiteBalance": {
    "WhiteBalanceMode": null
  },
  "Adjustment": {
    "ColorMatrix": null
  },
  "Rotation": {},
  "Direction": {
    "Vertical": null
  },
  "Network": {
    "ProxyURL": "http://no/sample/provided",
    "ProxyPort": 0,
    "ProxyUserName": "user",
    "IPAddress": "192.168.1.1",
    "SubnetMask": "255.255.0.0",
    "Gateway": "192.168.1.1",
    "DNS": "8.8.8.8",
    "NTP": "pool.ntp.org"
  },
  "Permission": {
    "FactoryReset": true
  }
}
""",
    ],
)
def test_validate_fields_added_dts_1003_backward_compatible(payload: str):
    device_config = DeviceConfiguration.model_validate_json(payload)

    assert device_config


def test_validate_fields_added_dts_1003_t3w():
    # Fields added for the t3w schema
    payload = """
{
  "Hardware": {
    "Sensor": "IMX500",
    "SensorId": "100A50500A2010072664012000000000",
    "KG": "1",
    "ApplicationProcessor": "ESP32",
    "LedOn": true
  },
  "Version": {
    "SensorFwVersion": "010707",
    "SensorLoaderVersion": "020301",
    "DnnModelVersion": ["0308000000000100"],
    "ApFwVersion": "D52408",
    "CameraSetupFileVersion": {
      "ColorMatrixStd": "123",
      "ColorMatrixCustom": "456",
      "GammaStd": "789",
      "GammaCustom": "098",
      "LSCISPStd": "765",
      "LSCISPCustom": "432",
      "LSCRawStd": "101",
      "LSCRawCustom": "234",
      "PreWBStd": "567",
      "PreWBCustom": "890",
      "DewarpStd": "987",
      "DewarpCustom": "654"
    }
  },
  "Status": {
    "Sensor": "Standby",
    "ApplicationProcessor": "Idle",
    "SensorTemperature": 50,
    "HoursMeter": 10
  },
  "OTA": {
    "UpdateModule": "SensorFw",
    "ReplaceNetworkID": "0308000000000101",
    "DeleteNetworkID": "0308000000000102",
    "PackageUri": "http://no/sample/provided",
    "DesiredVersion": "010707",
    "HashValue": "d9b6c7f0a7eefccf952a8acfc0fee9ef",
    "SensorFwLastUpdatedDate": "20241107085300",
    "SensorLoaderLastUpdatedDate": "20241007085300",
    "DnnModelLastUpdatedDate": ["20241028151808"],
    "ApFwLastUpdatedDate": "20241106085300",
    "CameraSetupFunction": "ColorMatrix",
    "CameraSetupMode": "custom",
    "UpdateProgress": 100,
    "UpdateStatus": "Done"
  },
  "Image": {
    "FrameRate": 2997,
    "DriveMode": 1
  },
  "Exposure": {
    "ExposureMode": "auto",
    "ExposureMaxExposureTime": 20,
    "ExposureMinExposureTime": 33,
    "ExposureMaxGain": 24,
    "AESpeed": 3,
    "ExposureCompensation": 6,
    "ExposureTime": 18,
    "ExposureGain": 1,
    "FlickerReduction": 7
  },
  "WhiteBalance": {
    "WhiteBalanceMode": "auto",
    "WhiteBalancePreset": 0,
    "WhiteBalanceSpeed": 3
  },
  "Adjustment": {
    "ColorMatrix": "std",
    "Gamma": "std",
    "LSC-ISP": "std",
    "LSC-Raw": "std",
    "PreWB": "std",
    "Dewarp": "off"
  },
  "Rotation": {
    "RotAngle": 0
  },
  "Direction": {
    "Vertical": "Normal",
    "Horizontal": "Normal"
  },
  "Network": {
    "ProxyURL": "http://no/sample/provided",
    "ProxyPort": 0,
    "ProxyUserName": "user",
    "IPAddress": "192.168.1.1",
    "SubnetMask": "255.255.0.0",
    "Gateway": "192.168.1.1",
    "DNS": "8.8.8.8",
    "NTP": "pool.ntp.org"
  },
  "Permission": {
    "FactoryReset": true
  },
  "Battery": {
    "Voltage": 150,
    "InUse": "primary",
    "Alarm": true
  },
  "FWOperation": {
     "OperatingMode": "Manual",
     "ErrorHandling": "AutoReboot",
     "PeriodicParameter": {
      "NetworkParameter" : "Save",
      "PrimaryInterval" :  {
          "ConfigInterval":240,
          "CaptureInterval":20,
          "BaseTime":"00:00",
          "UploadCount":1
      },
      "SecondaryInterval": {
          "ConfigInterval":0,
          "CaptureInterval":0,
          "BaseTime":"00:00",
          "UploadCount":0
      },
      "UploadInferenceParameter": {
          "UploadMethodIR":"BlobStorage",
          "StorageNameIR": "not_provided",
          "StorageSubDirectoryPathIR":"not_provided",
          "PPLParameter":"not_provided",
          "CropHOffset":0,
          "CropVOffset":0,
          "CropHSize":2028,
          "CropVSize":1520,
          "NetworkId":"999996"
      }
    }
  }
}
"""
    device_config = DeviceConfiguration.model_validate_json(payload)

    assert device_config.Battery.Voltage == 150
    assert device_config.Battery.InUse == "primary"
    assert device_config.Battery.Alarm
    assert device_config.FWOperation
    assert device_config.FWOperation.OperatingMode == "Manual"
    assert device_config.FWOperation.ErrorHandling == "AutoReboot"
    assert device_config.FWOperation.PeriodicParameter.NetworkParameter == "Save"
    assert (
        device_config.FWOperation.PeriodicParameter.PrimaryInterval.ConfigInterval
        == 240
    )
    assert (
        device_config.FWOperation.PeriodicParameter.PrimaryInterval.CaptureInterval
        == 20
    )
    assert (
        device_config.FWOperation.PeriodicParameter.PrimaryInterval.BaseTime == "00:00"
    )
    assert device_config.FWOperation.PeriodicParameter.PrimaryInterval.UploadCount == 1
    assert (
        device_config.FWOperation.PeriodicParameter.SecondaryInterval.ConfigInterval
        == 0
    )
    assert (
        device_config.FWOperation.PeriodicParameter.SecondaryInterval.CaptureInterval
        == 0
    )
    assert (
        device_config.FWOperation.PeriodicParameter.SecondaryInterval.BaseTime
        == "00:00"
    )
    assert (
        device_config.FWOperation.PeriodicParameter.SecondaryInterval.UploadCount == 0
    )
    assert (
        device_config.FWOperation.PeriodicParameter.UploadInferenceParameter.UploadMethodIR
        == "BlobStorage"
    )
    assert (
        device_config.FWOperation.PeriodicParameter.UploadInferenceParameter.StorageNameIR
        == "not_provided"
    )
    assert (
        device_config.FWOperation.PeriodicParameter.UploadInferenceParameter.StorageSubDirectoryPathIR
        == "not_provided"
    )
    assert (
        device_config.FWOperation.PeriodicParameter.UploadInferenceParameter.PPLParameter
        == "not_provided"
    )
    assert (
        device_config.FWOperation.PeriodicParameter.UploadInferenceParameter.CropHOffset
        == 0
    )
    assert (
        device_config.FWOperation.PeriodicParameter.UploadInferenceParameter.CropVOffset
        == 0
    )
    assert (
        device_config.FWOperation.PeriodicParameter.UploadInferenceParameter.CropHSize
        == 2028
    )
    assert (
        device_config.FWOperation.PeriodicParameter.UploadInferenceParameter.CropVSize
        == 1520
    )
    assert (
        device_config.FWOperation.PeriodicParameter.UploadInferenceParameter.NetworkId
        == "999996"
    )


@pytest.mark.parametrize(
    "payload",
    [
        """
{
  "Hardware": {
    "Sensor": "IMX500",
    "SensorId": "100A50500A2010072664012000000000",
    "KG": "1",
    "ApplicationProcessor": "ESP32",
    "LedOn": true
  },
  "Version": {
    "SensorFwVersion": "010707",
    "SensorLoaderVersion": "020301",
    "DnnModelVersion": ["0308000000000100"],
    "ApFwVersion": "D52408",
    "CameraSetupFileVersion": {
      "ColorMatrixStd": "123",
      "ColorMatrixCustom": "456",
      "GammaStd": "789",
      "GammaCustom": "098",
      "LSCISPStd": "765",
      "LSCISPCustom": "432",
      "LSCRawStd": "101",
      "LSCRawCustom": "234",
      "PreWBStd": "567",
      "PreWBCustom": "890",
      "DewarpStd": "987",
      "DewarpCustom": "654"
    }
  },
  "Status": {
    "Sensor": "Standby",
    "ApplicationProcessor": "Idle",
    "SensorTemperature": 50,
    "HoursMeter": 10
  },
  "OTA": {
    "UpdateModule": "SensorFw",
    "ReplaceNetworkID": "0308000000000101",
    "DeleteNetworkID": "0308000000000102",
    "PackageUri": "http://no/sample/provided",
    "DesiredVersion": "010707",
    "HashValue": "d9b6c7f0a7eefccf952a8acfc0fee9ef",
    "SensorFwLastUpdatedDate": "20241107085300",
    "SensorLoaderLastUpdatedDate": "20241007085300",
    "DnnModelLastUpdatedDate": ["20241028151808"],
    "ApFwLastUpdatedDate": "20241106085300",
    "CameraSetupFunction": "ColorMatrix",
    "CameraSetupMode": "custom",
    "UpdateProgress": 100,
    "UpdateStatus": "Done"
  },
  "Image": {
    "FrameRate": 2997,
    "DriveMode": 1
  },
  "Exposure": {
    "ExposureMode": "auto",
    "ExposureMaxExposureTime": 20,
    "ExposureMinExposureTime": 33,
    "ExposureMaxGain": 24,
    "AESpeed": 3,
    "ExposureCompensation": 6,
    "ExposureTime": 18,
    "ExposureGain": 1,
    "FlickerReduction": 7
  },
  "WhiteBalance": {
    "WhiteBalanceMode": "auto",
    "WhiteBalancePreset": 0,
    "WhiteBalanceSpeed": 3
  },
  "Adjustment": {
    "ColorMatrix": "std",
    "Gamma": "std",
    "LSC-ISP": "std",
    "LSC-Raw": "std",
    "PreWB": "std",
    "Dewarp": "off"
  },
  "Rotation": {
    "RotAngle": 0
  },
  "Direction": {
    "Vertical": "Normal",
    "Horizontal": "Normal"
  },
  "Network": {
    "ProxyURL": "http://no/sample/provided",
    "ProxyPort": 0,
    "ProxyUserName": "user",
    "IPAddress": "192.168.1.1",
    "SubnetMask": "255.255.0.0",
    "Gateway": "192.168.1.1",
    "DNS": "8.8.8.8",
    "NTP": "pool.ntp.org"
  },
  "Permission": {
    "FactoryReset": true
  }
}
""",
        """
{
  "Hardware": {
    "Sensor": "IMX500",
    "SensorId": "100A50500A2010072664012000000000",
    "KG": "1",
    "ApplicationProcessor": "ESP32",
    "LedOn": true
  },
  "Version": {
    "SensorFwVersion": "010707",
    "SensorLoaderVersion": "020301",
    "DnnModelVersion": ["0308000000000100"],
    "ApFwVersion": "D52408",
    "CameraSetupFileVersion": {
      "ColorMatrixStd": "123",
      "ColorMatrixCustom": "456",
      "GammaStd": "789",
      "GammaCustom": "098",
      "LSCISPStd": "765",
      "LSCISPCustom": "432",
      "LSCRawStd": "101",
      "LSCRawCustom": "234",
      "PreWBStd": "567",
      "PreWBCustom": "890",
      "DewarpStd": "987",
      "DewarpCustom": "654"
    }
  },
  "Status": {
    "Sensor": "Standby",
    "ApplicationProcessor": "Idle",
    "SensorTemperature": 50,
    "HoursMeter": 10
  },
  "OTA": {
    "UpdateModule": "SensorFw",
    "ReplaceNetworkID": "0308000000000101",
    "DeleteNetworkID": "0308000000000102",
    "PackageUri": "http://no/sample/provided",
    "DesiredVersion": "010707",
    "HashValue": "d9b6c7f0a7eefccf952a8acfc0fee9ef",
    "SensorFwLastUpdatedDate": "20241107085300",
    "SensorLoaderLastUpdatedDate": "20241007085300",
    "DnnModelLastUpdatedDate": ["20241028151808"],
    "ApFwLastUpdatedDate": "20241106085300",
    "CameraSetupFunction": "ColorMatrix",
    "CameraSetupMode": "custom",
    "UpdateProgress": 100,
    "UpdateStatus": "Done"
  },
  "Image": {
    "FrameRate": 2997,
    "DriveMode": 1
  },
  "Exposure": {
    "ExposureMode": "auto",
    "ExposureMaxExposureTime": 20,
    "ExposureMinExposureTime": 33,
    "ExposureMaxGain": 24,
    "AESpeed": 3,
    "ExposureCompensation": 6,
    "ExposureTime": 18,
    "ExposureGain": 1,
    "FlickerReduction": 7
  },
  "WhiteBalance": {
    "WhiteBalanceMode": "auto",
    "WhiteBalancePreset": 0,
    "WhiteBalanceSpeed": 3
  },
  "Adjustment": {
    "ColorMatrix": "std",
    "Gamma": "std",
    "LSC-ISP": "std",
    "LSC-Raw": "std",
    "PreWB": "std",
    "Dewarp": "off"
  },
  "Rotation": {
    "RotAngle": 0
  },
  "Direction": {
    "Vertical": "Normal",
    "Horizontal": "Normal"
  },
  "Network": {
    "ProxyURL": "http://no/sample/provided",
    "ProxyPort": 0,
    "ProxyUserName": "user",
    "IPAddress": "192.168.1.1",
    "SubnetMask": "255.255.0.0",
    "Gateway": "192.168.1.1",
    "DNS": "8.8.8.8",
    "NTP": "pool.ntp.org"
  },
  "Permission": {
    "FactoryReset": true
  },
  "Battery": {
    "Voltage": null,
    "Alarm": null
  },
  "FWOperation": {
     "ErrorHandling": null,
     "PeriodicParameter": {
      "NetworkParameter" : "Save",
      "PrimaryInterval" :  {
          "CaptureInterval":null,
          "BaseTime":null
      },
      "UploadInferenceParameter": {
          "UploadMethodIR":null,
          "CropHOffset":null
      }
    }
  }
}
""",
    ],
)
def test_validate_fields_added_dts_1003_backward_compatible_t3w(payload: str):
    # Fields added for the t3w schema
    device_config = DeviceConfiguration.model_validate_json(payload)

    assert device_config
