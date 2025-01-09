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
import random
import string
from datetime import datetime


def random_text(characters: str = string.ascii_letters, length: int = 10) -> str:
    return "".join(random.choices(characters, k=length))


def random_alphanumeric(length: int = 10) -> str:
    return random_text(characters=string.ascii_letters + string.digits, length=length)


def random_int(min: int = 0, max: int = 2**31) -> int:
    return random.randint(min, max)


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
