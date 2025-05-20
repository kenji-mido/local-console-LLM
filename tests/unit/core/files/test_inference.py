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
from unittest.mock import MagicMock

import pytest
from local_console.core.camera.streaming import inference_dir_for
from local_console.core.config import Config
from local_console.core.files.device import InferenceFileManager
from local_console.core.files.exceptions import FileNotFound
from local_console.core.files.inference import Inference
from local_console.core.files.inference import InferenceManager
from local_console.core.files.inference import InferenceType

from tests.strategies.samplers.configs import DeviceConnectionSampler
from tests.unit.core.files.test_devices import device_services_and_state


INFERENCE_FLATBUFFER_SAMPLE = "AMBdPQAALrwAgAA9AFAcPgBgJz4AAAI8AAA3PADgCz4AoIU9AABKPADAyD0AQAG9AADEOwAAJDwAoA0+ALBUPgAARDwAsIM+ABAGPgAAcLwA2Ms+AAC8OwDgAz4AgMO8AHACPgDwyj4AsB4+ACBHPgAg0D0AAO47AAC4uwDQBz4AAI48AIApPQAAHLsAcCY+AABcuwCAAT0AAFw8AABQOgCg1D0AMD4+AAAgOgDAoD0AAK67AHAUPgBAjj4AIOU9AACJPQDAzT0AwL09AACEOwCANj0AcHo+ACBQPgCARr0AILY+AIBaPgAAgLgAwBc9AAAwOgAAaTwAABO8AMChPgAUAz8A8Ek+AACsOwBgWD8AFBA/AGg8PwAAQLoAMEk+AIgGPwD0YD8AjBE/ANBlPwAo7j4AePA+AEg1PwAAyDoAgAs/AAwdPwBAwD0AqFI/ACxMPwAgID4AAFA7AGjlPgAAXDsAAPw7AFjzPgBARz4AAMA5AFAEPwAAsjsAtA8/ALwrPwD8CT8AgCE+AJxZPwAMHT8AAKs+APgEPwBomT4AIJw+APChPgDEDD8AAJ8+ANiSPgCwlD4AsIg+AFj2PgBARj4A4B4+AABpPgA4pj4AAE0+ALDbPgDwZD4AwJ0+AIR8PwAQmj4AMIY+AFjgPgDIgz4AMBM/ANiaPgAQsz4ACNE+APAdPgAgFz4AMGM+ACAOPgDgXj4AkCI+ANiZPgBgkz0A4I8+AHDtPgBAdj0AkDU+AEibPgAAyD0AIEg+AODwPQDYnT4AwBE/AFA4PgAAST4AIF0+ABhwPwCAoz4A4Bw/ANijPgBQjD4AOCA/AKB3PwCArD4AsCk+AIjpPgBAVj0AKN4+AJBvPgCgwT4A1Bo/AJiNPgBA9z0AQH4/AGwoPwBQeT8AuFI/APjfPgCIMj8APH4/ANQ/PwDYfz8A9CU/AMwkPwA4fD8AQHY9APhkPwB0ND8AQC4+APBzPwDMez8AYGw+AMCTPQB8Jz8AcCA+AADBPQDEIT8AEJk+AIB0PQCoFj8AYOM9AKxBPwDGgD8ATC0/AIBlPgBsbD8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAcj8AAJY+AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQA=="
INFERENCE_CONTENT_SAMPLE = (
    """{
    "DeviceID":"sid-100A50500A2010072664012000000000",
    "ModelID":"0308000000000100",
    "Image":true,
    "Inferences":[
        {"T":"a-fake-timestamp",
        "O":"%s",
        "F":0,
        "unexpected_field":"with value"
        }],
    "additional_field":"some value"
}
"""
    % INFERENCE_FLATBUFFER_SAMPLE
)

INFERENCE_CONTENT_SAMPLE_OUT = (
    """{
    "DeviceID":"sid-100A50500A2010072664012000000000",
    "ModelID":"0308000000000100",
    "Image":true,
    "Inferences":[
        {"T":"a-fake-timestamp",
        "O":"%s"
        }]
}
"""
    % INFERENCE_FLATBUFFER_SAMPLE
)


def test_inference_model_no_fieldtype() -> None:
    without_fieldtype = INFERENCE_CONTENT_SAMPLE.replace('"F":0,', "")
    loaded = Inference.model_validate_json(without_fieldtype)

    assert loaded.device_id == "sid-100A50500A2010072664012000000000"
    assert loaded.model_id == "0308000000000100"
    assert loaded.image
    assert len(loaded.inferences) == 1
    assert loaded.inferences[0].t == "a-fake-timestamp"
    assert loaded.inferences[0].o == INFERENCE_FLATBUFFER_SAMPLE
    assert loaded.inferences[0].f is None

    assert json.loads(
        loaded.model_dump_json(by_alias=True, exclude_none=True)
    ) == json.loads(without_fieldtype)


def test_inference_model_with_fieldtype() -> None:

    dummy_inference = [{"foo": "bar"}]
    with_fieldtype = INFERENCE_CONTENT_SAMPLE.replace('"F":0,', '"F":1,').replace(
        f'"{INFERENCE_FLATBUFFER_SAMPLE}"', json.dumps(dummy_inference)
    )
    loaded = Inference.model_validate_json(with_fieldtype)

    assert loaded.device_id == "sid-100A50500A2010072664012000000000"
    assert loaded.model_id == "0308000000000100"
    assert loaded.image
    assert len(loaded.inferences) == 1
    assert loaded.inferences[0].t == "a-fake-timestamp"
    assert loaded.inferences[0].o == dummy_inference
    assert loaded.inferences[0].f == InferenceType.JSON

    serialized = loaded.model_dump_json(by_alias=True)
    assert '"F":1,' in serialized


@pytest.mark.trio
async def test_list_inferences(tmp_path) -> None:
    async with device_services_and_state(tmp_path) as (
        device_services,
        dev_id,
    ):
        base = inference_dir_for(dev_id)
        files = [
            base / "20241003093439234.txt",
            base / "20241003093439235.txt",
        ]
        for file in files:
            file.write_text(INFERENCE_CONTENT_SAMPLE)
        base.joinpath("not_an_inference.txt").write_text("Not even a json")
        subdir = base / "subdir"
        subdir.mkdir()

        fm = InferenceFileManager(device_services)
        manager = InferenceManager(fm)
        infs = manager.list(dev_id)

        assert [i.inference for i in infs] == [
            Inference.model_validate_json(INFERENCE_CONTENT_SAMPLE),
            Inference.model_validate_json(INFERENCE_CONTENT_SAMPLE),
        ]
        assert sorted([i.path for i in infs]) == sorted(files)


@pytest.mark.trio
async def test_get_inference(tmp_path) -> None:
    async with device_services_and_state(tmp_path) as (
        device_services,
        dev_id,
    ):
        base = inference_dir_for(dev_id)
        inference_id = "20241003093439234.txt"
        base.joinpath(inference_id).write_text(INFERENCE_CONTENT_SAMPLE)

        fm = InferenceFileManager(device_services)
        manager = InferenceManager(fm)
        inf = manager.get(dev_id, inference_id)

        assert inf.inference == Inference.model_validate_json(INFERENCE_CONTENT_SAMPLE)
        assert inf.path == base / inference_id


@pytest.mark.trio
async def test_get_inference_not_found(tmp_path) -> None:
    async with device_services_and_state(tmp_path) as (
        device_services,
        dev_id,
    ):
        fm = InferenceFileManager(device_services)
        manager = InferenceManager(fm)

        with pytest.raises(FileNotFound) as error:
            manager.get(dev_id, "file_does_not_exists")

        assert str(error.value) == "Inference file 'file_does_not_exists' not found"


def test_get_inference_inconsistency(tmp_path) -> None:
    inference_path = tmp_path / "20241003093439234.txt"
    inference_path.write_text(INFERENCE_CONTENT_SAMPLE)
    device = DeviceConnectionSampler().sample()
    device.persist.device_dir_path = tmp_path
    Config().data.devices = [device]

    fm = MagicMock(spec=InferenceFileManager)
    fm.list_for.return_value = [inference_path, inference_path]
    manager = InferenceManager(fm)

    with pytest.raises(AssertionError) as error:
        manager.get(device.id, "20241003093439234.txt")

    assert (
        str(error.value)
        == "Multiple inference files with id '20241003093439234.txt' exist"
    )


@pytest.mark.trio
async def test_get_inference_invalid_file(tmp_path) -> None:
    async with device_services_and_state(tmp_path) as (
        device_services,
        dev_id,
    ):
        files = [
            tmp_path / f"{dev_id}/Metadata/20241003093439234.txt",
            tmp_path / f"{dev_id}/Metadata/20241003093439235.txt",
        ]
        files[0].write_text(INFERENCE_CONTENT_SAMPLE)
        files[1].write_bytes(b"\x80")

        fm = InferenceFileManager(device_services)
        manager = InferenceManager(fm)

        infs = manager.list(dev_id)
        assert len(infs) == 1

        assert infs[0].inference == Inference.model_validate_json(
            INFERENCE_CONTENT_SAMPLE
        )
        assert infs[0].path == files[0]
