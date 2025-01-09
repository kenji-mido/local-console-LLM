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
from unittest.mock import AsyncMock
from unittest.mock import call
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from local_console.utils.trio import lock_until_started
from local_console.utils.trio import TaskStatus
from local_console.utils.trio import TimeoutConfig


@pytest.mark.parametrize(
    "max, interval, num_calls",
    [
        (5, 1, 5),  # happy sample
        (60, 0.2, 300),  # defaults
        (7.8, 2.5, 3),  # Positive floats, expected truncation
        (10.0, 3.0, 3),  # Division with no decimal part
        (-7.8, 2.5, 1),  # Negative numerator, positive denominator
        (7.8, -2.5, 3),  # Positive numerator, negative denominator
        (-7.8, -2.5, 1),  # Negative numerator and denominator
        (0.0, 2.5, 1),  # Zero numerator
        (2.5, 7.8, 1),  # Result less than 1
        (5.0, 2.0, 2),  # Exact integer result
        (5.0, 0, 100),  # Division by zero
        (0.0, 0.0, 1),  # Zero divided by zero
    ],
)
def test_num_of_iterations(max, interval, num_calls) -> None:
    assert (
        TimeoutConfig(
            timeout_in_seconds=max, pollin_interval_in_seconds=interval
        ).num_of_iterations()
        == num_calls
    )


@pytest.mark.trio
async def test_timeout() -> None:
    status = MagicMock()
    status.return_value = TaskStatus.SUCCESS

    await lock_until_started(status)

    status.assert_called_once()


@pytest.mark.trio
@patch("local_console.utils.trio.trio", new_callable=AsyncMock)
async def test_timeout_calls(mocked_trio: AsyncMock) -> None:
    status = MagicMock()
    status.side_effect = [TaskStatus.STARTING, TaskStatus.ERROR, TaskStatus.SUCCESS]
    timeout = TimeoutConfig(pollin_interval_in_seconds=1, timeout_in_seconds=5)

    with pytest.raises(TimeoutError) as error:
        await lock_until_started(status, config=timeout)

    assert status.call_count == 2
    mocked_trio.sleep.assert_has_awaits(
        [call(timeout.pollin_interval_in_seconds) for _ in range(1)]
    )
    assert str(error.value) == "Timeout exceeded"


@pytest.mark.trio
@patch("local_console.utils.trio.trio", new_callable=AsyncMock)
async def test_raise_timeout_exception(mocked_trio: AsyncMock) -> None:
    status = MagicMock()
    status.return_value = TaskStatus.STARTING
    expected_error_message = "On time out complain with this"
    timeout = TimeoutConfig(pollin_interval_in_seconds=1, timeout_in_seconds=5)
    with pytest.raises(TimeoutError) as error:
        await lock_until_started(status, message=expected_error_message, config=timeout)

    assert status.call_count == 5
    mocked_trio.sleep.assert_has_awaits(
        [call(timeout.pollin_interval_in_seconds) for _ in range(5)]
    )

    assert str(error.value) == expected_error_message
