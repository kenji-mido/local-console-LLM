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
from local_console.core.camera.schemas import PropertiesReport
from local_console.core.camera.v2.components.device_info import AIModel
from local_console.core.camera.v2.components.device_info import Chip
from local_console.core.camera.v2.edge_system_common import DeviceInfo
from local_console.core.camera.v2.edge_system_common import EdgeSystemCommon
from local_console.core.helpers import merge_model_instances


def test_model_instance_merging_for_properties_report():

    target = PropertiesReport()
    source = PropertiesReport(sensor_status="idle")

    # simplest case: attribute in source is non-default, and default in target
    merge_model_instances(target, source)
    assert target.sensor_status == "idle"

    # no-overwrite: attribute in target is non-default, and default in source
    target.cam_fw_status = "thunder"
    source.cam_fw_status = None
    merge_model_instances(target, source)
    assert target.cam_fw_status == "thunder"

    # proper overwrite: attribute is non-default on both target and source; target gets updated
    target.sensor_hardware = "rain"
    source.sensor_hardware = "clear"
    merge_model_instances(target, source)
    assert target.sensor_hardware == "clear"

    # the merging must have kept the values of the other attributes
    assert target.sensor_status == "idle"
    assert target.cam_fw_status == "thunder"


def test_model_instance_merging_for_v2_report():

    target = EdgeSystemCommon()
    source = EdgeSystemCommon(
        device_info=DeviceInfo(
            device_manifest="b64blob",
            chips=[
                Chip(
                    name="sensor",
                    id="",
                    hardware_version="",
                    temperature=23,
                    loader_version="",
                    loader_hash="",
                    update_date_loader="",
                    firmware_version="",
                    firmware_hash="",
                    update_date_firmware="",
                    ai_models=[
                        AIModel(
                            version="",
                            hash="",
                            update_date="",
                        )
                    ],
                )
            ],
        )
    )

    merge_model_instances(target, source)
    assert target.system_info is None
    assert (
        next(c.temperature for c in target.device_info.chips if c.name == "sensor")
        == 23
    )
