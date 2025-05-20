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
from collections.abc import Awaitable
from typing import Callable
from typing import Concatenate
from typing import ParamSpec
from typing import TypeVar

import trio
from _pytest.monkeypatch import MonkeyPatch

P = ParamSpec("P")
Tcls = TypeVar("Tcls")
R = TypeVar("R")


def extend_method(
    cls: type[Tcls],
    method_name: str,
    extension_func: Callable[[Tcls, R], None],
    monkeypatch: MonkeyPatch,
) -> None:
    """
    Replaces `cls.method_name` with a wrapped version that:
      1) Calls the original method,
      2) Then invokes `extension_func(self, result)` for further inspection.

    monkeypatch:    A pytest monkeypatch fixture instance.
    cls:            The class containing the method to be patched.
    method_name:    Name of the method within `cls`.
    extension_func: A callable accepting (self, original_result).
                    It is invoked after the original method completes.
    """
    assert hasattr(cls, method_name)
    original_method: Callable[Concatenate[Tcls, P], R] = getattr(cls, method_name)

    def wrapper(self: Tcls, *args: P.args, **kwargs: P.kwargs) -> R:
        result: R = original_method(self, *args, **kwargs)
        extension_func(self, result)
        return result

    monkeypatch.setattr(cls, method_name, wrapper)


def extend_method_async(
    cls: type[Tcls],
    method_name: str,
    extension_func_async: Callable[[Tcls, R], Awaitable[None]],
    monkeypatch: MonkeyPatch,
) -> None:
    """
    Replaces `cls.method_name` with a wrapped version that:
      1) Calls the original async method,
      2) Then invokes `extension_func_async(self, result)` for further inspection.

    monkeypatch:          A pytest monkeypatch fixture instance.
    cls:                  The class containing the method to be patched.
    method_name:          Name of the method within `cls`.
    extension_func_async: An async callable accepting (self, original_result).
                          It is invoked after the original method completes.
    """
    assert hasattr(cls, method_name)
    original_method: Callable[Concatenate[Tcls, P], Awaitable[R]] = getattr(
        cls, method_name
    )

    async def wrapper(self: Tcls, *args: P.args, **kwargs: P.kwargs) -> R:
        result = await original_method(self, *args, **kwargs)
        await extension_func_async(self, result)
        return result

    monkeypatch.setattr(cls, method_name, wrapper)


class MethodObserver:
    """
    Provides a simple interface for doing a async await for
    a method in an object to have been called, by leveraging
    `extend_method_async` above
    """

    def __init__(self, monkeypatch: MonkeyPatch) -> None:
        self._mp = monkeypatch
        self._signal = trio.Event()

    async def wait_for(self) -> None:
        await self._signal.wait()
        self.reset()

    def reset(self) -> None:
        self._signal = trio.Event()

    async def set(self, class_self: Tcls, result: R) -> None:
        self._signal.set()

    def hook(self, target_class: type[Tcls], method: str) -> None:
        extend_method_async(target_class, method, self.set, self._mp)
