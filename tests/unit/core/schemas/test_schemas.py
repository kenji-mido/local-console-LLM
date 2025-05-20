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

import pytest
from local_console.core.camera.enums import UnitScale
from local_console.core.enums import DEFAULT_PERSIST_SETTINGS
from local_console.core.schemas.schemas import Persist


@pytest.mark.parametrize(
    "input,expected",
    [
        ["{}", Persist()],
        [
            """
{
        "module_file": null,
        "ai_model_file": null,
        "device_dir_path": null,
        "size": 100,
        "unit": "MB",
        "vapp_type": "image",
        "vapp_schema_file": null,
        "vapp_config_file": null,
        "vapp_labels_file": null
      }
""",
            DEFAULT_PERSIST_SETTINGS,
        ],
        [
            """
{
    "module_file": "module_file",
    "ai_model_file": "ai_model_file",
    "device_dir_path": "device_dir_path",
    "size": 123,
    "unit": "GB",
    "vapp_type": "image",
    "vapp_schema_file": "vapp_schema_file",
    "vapp_config_file": "vapp_config_file",
    "vapp_labels_file": "vapp_labels_file"
}""",
            Persist(
                module_file="module_file",
                ai_model_file="ai_model_file",
                device_dir_path=Path("device_dir_path"),
                size=123,
                unit=UnitScale.GB,
                vapp_type="image",
                vapp_schema_file="vapp_schema_file",
                vapp_config_file="vapp_config_file",
                vapp_labels_file="vapp_labels_file",
            ),
        ],
        # Backward compatible
        [
            """
{
    "size":123,
    "unit":"kb"
}
""",
            Persist(size=123, unit=UnitScale.KB),
        ],
        ['{"size":54,"unit":"Mb"}', Persist(size=54, unit=UnitScale.MB)],
    ],
)
def test_load_persist(input: str, expected: Persist) -> None:
    loaded = Persist.model_validate_json(input)
    print(loaded)
    print(expected)
    assert loaded == expected
