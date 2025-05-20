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
This provides a nicer way to document methods of `core.machine.Camera`
that depend on the current camera state.
"""
import functools
from collections.abc import Sequence
from typing import Callable
from typing import Concatenate
from typing import ParamSpec
from typing import Protocol
from typing import TypeVar

from local_console.core.camera.states.base import StateWithProperties
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes


class StateMachineLike(Protocol):
    """
    Basic model of something that holds a StateWithProperties
    """

    @property
    def _state(self) -> StateWithProperties: ...


P = ParamSpec("P")
R = TypeVar("R")
T = TypeVar("T", bound=StateMachineLike)


def only_in_states(
    allowed_states: Sequence[type[StateWithProperties]],
) -> Callable[[Callable[Concatenate[T, P], R]], Callable[Concatenate[T, P], R]]:
    """
    A decorator that checks if the current state is an instance of any one
    of the types set in `allowed_states. If not, it raises an `UserException`
    with the `EXTERNAL_INVALID_METHOD_DURING_STATE` error code.
    """

    def decorator(
        func: Callable[Concatenate[T, P], R]
    ) -> Callable[Concatenate[T, P], R]:

        @functools.wraps(func)
        def wrapper(self: T, *args: P.args, **kwargs: P.kwargs) -> R:
            if not any(isinstance(self._state, t) for t in allowed_states):
                allowed_names = [t.__name__ for t in allowed_states]
                raise UserException(
                    ErrorCodes.EXTERNAL_INVALID_METHOD_DURING_STATE,
                    f"Attempted to invoke method {func.__name__} while camera is in state {type(self._state).__name__}"
                    f", which is not in the allowed set: {allowed_names}",
                )
            return func(self, *args, **kwargs)

        return wrapper

    return decorator
