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
from local_console.core.helpers import is_default_or_none
from pydantic import BaseModel


def test_is_default_or_none():
    assert is_default_or_none(None)
    assert is_default_or_none([])
    assert is_default_or_none(())


def test_is_not_default_or_none():
    assert not is_default_or_none(False)
    assert not is_default_or_none(True)
    assert not is_default_or_none("")
    assert not is_default_or_none("a")
    assert not is_default_or_none([1, 2, 3])
    assert not is_default_or_none((1, 2, 3))
    assert not is_default_or_none(0)
    assert not is_default_or_none(0.0)
    assert not is_default_or_none(2)
    assert not is_default_or_none(0.000001)

    class Dummy(BaseModel):
        pass

    assert not is_default_or_none(Dummy())
