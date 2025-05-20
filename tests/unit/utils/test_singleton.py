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
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
import trio
from local_console.utils.singleton import Singleton
from trio_util import wait_all


def test_instance_variables():

    class A(metaclass=Singleton):
        def __init__(self) -> None:
            self.value = 0

    assert A._Singleton__instance is None

    instance_0 = A()
    assert A._Singleton__instance == instance_0
    assert instance_0.value == 0

    instance_1 = A()
    assert A._Singleton__instance == instance_1
    instance_1.value = 12345
    assert instance_0.value == 12345

    assert id(instance_0) == id(instance_1)


def test_class_variables():

    class B(metaclass=Singleton):
        cvalue = "?"

    assert B._Singleton__instance is None

    instance_0 = B()
    assert B._Singleton__instance == instance_0
    assert instance_0.cvalue == "?"

    instance_1 = B()
    assert B._Singleton__instance == instance_1
    instance_1.cvalue = "!"
    assert instance_0.cvalue == "!"

    assert id(instance_0) == id(instance_1)


@pytest.fixture
def singleton_class():
    """
    Simple user of the Singleton pattern.

    It is defined within a fixture so as to ensure that the
    class gets defined anew for each test.
    """

    class TSCounter(metaclass=Singleton):

        def __init__(self):
            self._lock = threading.Lock()
            self._counter = 0

        def bump(self):
            with self._lock:
                self._counter += 1

        def clear(self):
            with self._lock:
                self._counter = 0

    yield TSCounter


@pytest.mark.parametrize("num_threads, num_operations", [(50, 500), (100, 100)])
def test_thread_safety_sync(num_threads, num_operations, singleton_class):

    # Each thread will bump the singleton's counter
    def worker(thread_id):
        for i in range(num_operations):
            singleton_class().bump()

            # Random short sleep to increase the chance of context switching
            # (and thus concurrency collisions).
            time.sleep(random.uniform(1e-3, 5e-3))

    singleton_class().clear()
    # Run all threads in a ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker, tid) for tid in range(num_threads)]
        for f in futures:
            f.result()

    assert singleton_class()._counter == num_operations * num_threads


@pytest.mark.parametrize("num_threads, num_operations", [(50, 500), (100, 100)])
@pytest.mark.trio
async def test_thread_safety_async(
    num_threads, num_operations, singleton_class, nursery
):

    # Each task will bump the singleton's counter
    async def task(thread_id, task_status=trio.TASK_STATUS_IGNORED):
        event = trio.Event()
        task_status.started(event)

        for i in range(num_operations):
            singleton_class().bump()

            # Random short sleep to increase the chance of context switching
            # (and thus concurrency collisions).
            await trio.sleep(random.uniform(1e-3, 5e-3))

        event.set()

    # Spawn all tasks
    events = [await nursery.start(task, tid) for tid in range(num_threads)]
    await wait_all(*(e.wait for e in events))

    assert singleton_class()._counter == num_operations * num_threads


def test_inheritance(singleton_class):
    class ChildCounter(singleton_class):
        """
        To test that the singleton is kept separate from child classes.
        """

    assert ChildCounter()._counter == 0
    assert singleton_class()._counter == 0

    for _ in range(3):
        ChildCounter().bump()

    assert ChildCounter()._counter == 3
    assert singleton_class()._counter == 0
