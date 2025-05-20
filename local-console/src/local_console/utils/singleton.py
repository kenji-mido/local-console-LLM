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
import threading
from typing import Any
from typing import Generic
from typing import TypeVar


_T = TypeVar("_T")


class Singleton(type, Generic[_T]):
    """
    Composable implementation of the Singleton
    pattern with generic type annotations.

    Uses a `Lock` object to provide thread-safety.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.__instance: _T | None = None
        self.__lock = threading.Lock()
        super().__init__(*args, **kwargs)

    def __call__(self, *args: Any, **kwargs: Any) -> _T:
        if self.__instance is None:
            with self.__lock:
                # The repeated check below averts a race condition
                # with the creation of the instance by another thread.
                if not self.__instance:
                    self.__instance = super().__call__(*args, **kwargs)
            return self.__instance
        else:
            return self.__instance
