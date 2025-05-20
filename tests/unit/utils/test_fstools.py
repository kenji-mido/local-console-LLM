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
import contextlib
import logging
import os
import random
import threading
import time
from collections import OrderedDict
from collections.abc import Generator
from collections.abc import Iterator
from itertools import cycle
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from local_console.core.camera.enums import UnitScale
from local_console.core.config import Config
from local_console.core.error.base import UserException
from local_console.core.schemas.schemas import Persist
from local_console.utils.fstools import check_and_create_directory
from local_console.utils.fstools import DirectoryMonitor
from local_console.utils.fstools import FileInfo
from local_console.utils.fstools import FileInfoContainer
from local_console.utils.fstools import size_unit_to_bytes
from local_console.utils.fstools import StorageSizeWatcher
from watchdog.events import FileSystemEvent
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from tests import not_raises

logger = logging.getLogger(__name__)


class FileCreator:
    def __init__(self) -> None:
        self.age = 0

    def __call__(self, path: Path) -> None:
        path.write_bytes(b"0" * 1024)  # This matches usage of UnitScale.KB by default
        os.utime(path, ns=(self.age, self.age))
        self.age += 1


@pytest.fixture
def file_creator():
    yield FileCreator()


def persist(
    base: Path | None = None,
    inference: Path | None = None,
    size: int = 1,
) -> Persist:
    return Persist(
        device_dir_path=base if base else None,
        size=size,
        unit=UnitScale.KB,
    )


@pytest.fixture
def dir_layout(tmpdir, file_creator) -> Generator[[Path, int, int], None, None]:
    _id = 1883

    Config().update_persistent_attr(_id, "device_dir_path", Path(tmpdir))
    base_dir = tmpdir.mkdir(str(_id))
    image_dir = base_dir.mkdir("Images")
    inference_dir = base_dir.mkdir("Metadata")

    entries = [
        image_dir.join("fileA"),
        inference_dir.join("fileB"),
        image_dir.mkdir("sub").join("file0"),
        image_dir.join("sub").mkdir("subsub").join("file0"),
    ]
    # Make all entries, files of size 1 kB
    for e in entries:
        file_creator(Path(e))

    size = len(entries) * 1024
    return [
        Path(tmpdir),
        size,
        _id,
    ]


def create_new(root: Path, file_creator) -> Path:
    new_file = root / f"{random.randint(1, int(1e6))}"
    file_creator(new_file)
    return new_file


def test_regular_sequence_base(dir_layout, file_creator):
    dir_base, size, _id = dir_layout
    w = StorageSizeWatcher(persist(size=1), check_frequency=10)
    assert w.state == StorageSizeWatcher.State.Initialized

    w.apply(persist(size=1, base=dir_base), _id)
    assert w.state == StorageSizeWatcher.State.Configured

    w.gather()
    assert w.state == StorageSizeWatcher.State.Accumulating
    assert w.content.size == 1024

    w.incoming(create_new(dir_base / f"{_id}/Images", file_creator))
    assert w.state == StorageSizeWatcher.State.Accumulating
    assert w.content.size == 1024


def test_no_purge_on_apply(dir_layout) -> None:
    dir_base, size, _id = dir_layout

    # apply() does not update the size tally
    conf = persist(base=dir_base, size=size / 1024)
    w = StorageSizeWatcher(conf)
    w.apply(conf, _id)
    assert w.content.size == 0

    # Need to gather() for the tally to be updated
    w.gather()
    oldest_age = w.content.older[0][2].age
    assert w.content.size == size
    assert oldest_age == 0

    # Now, configuration is updated
    conf.size -= 1
    w.apply(conf, _id)
    oldest_age = w.content.older[0][2].age
    assert w.content.size == size
    assert oldest_age == 0

    # Again, need to gather() for the tally to be updated
    w.gather()
    oldest_age = w.content.older[0][2].age
    assert oldest_age == 1
    assert w.content.size == size - 1024


def test_pre_add_checking(dir_layout, file_creator) -> None:
    dir_base, size, _id = dir_layout

    # Initial state
    conf = persist(base=dir_base, size=size / 1024)
    w = StorageSizeWatcher(conf)
    w.apply(conf, _id)
    w.gather()
    assert w.content.size == size

    # preemptive verification
    assert w.current_limit == size
    assert w.content.size == size
    assert w.can_accept()

    w.incoming(
        create_new(dir_base / str(_id) / "Images", file_creator), prune_enabled=False
    )
    assert w.current_limit == size
    assert w.content.size > size
    assert not w.can_accept()


def test_adding_more_files_with_limit(dir_layout, file_creator) -> None:
    dir_base, size, _id = dir_layout
    conf = persist(base=dir_base, size=size / 1024)

    w = StorageSizeWatcher(conf)
    w.apply(conf, _id)
    w.gather()
    assert w.content.size == size
    oldest_age = w.content.older[0][2].age
    # Test creating and registering new files
    # in lockstep
    num_new_files = random.randint(5, 20)
    for _ in range(num_new_files):
        target = f"{_id}/" + random.choice(("Images", "Metadata"))
        w.incoming(create_new(dir_base / target, file_creator))
    assert w._consistency_check()
    assert w.content.size == size
    # This is due to the timestamp mocking, as each new file
    # is timestamped one time unit later than the previous.
    expected_oldest_age = oldest_age + num_new_files
    oldest_age = w.content.older[0][2].age
    assert oldest_age == expected_oldest_age


def test_consistency_check(dir_layout, file_creator) -> None:
    dir_base, size, _id = dir_layout
    conf = persist(base=dir_base, size=size / 1024)

    w = StorageSizeWatcher(conf)
    w.apply(conf, _id)
    w.gather()
    oldest_age = w.content.older[0][2].age
    # Test creating and registering new files
    # not in lockstep
    num_new_files = random.randint(5, 20)
    for _ in range(num_new_files):
        target = f"{_id}/" + random.choice(("Images", "Metadata"))
        create_new(dir_base / target, file_creator)
    # although consistency_check restores consistency,
    # it returns whether state was consistent before
    assert not w._consistency_check()
    # hence, a further call should indicate consistency.
    assert w._consistency_check()
    expected_oldest_age = oldest_age + num_new_files

    # However, pruning is still necessary:
    oldest_age = w.content.older[0][2].age
    assert oldest_age != expected_oldest_age
    assert w.content.size != size
    w._prune()
    oldest_age = w.content.older[0][2].age
    assert oldest_age == expected_oldest_age
    assert w.content.size == size


def test_inconsistency_on_unexpected_deletion(dir_layout, caplog, file_creator):
    dir_base, size, _id = dir_layout
    # Have the consistency check executed on the second incoming file
    conf = persist(base=dir_base, size=1 + size / 1024)
    w = StorageSizeWatcher(conf, check_frequency=2)
    w.apply(conf, _id)
    w.gather()

    # Regular update
    to_delete_later = create_new(dir_base / f"{_id}/Metadata", file_creator)
    w.incoming(to_delete_later)

    # Unrecorded update: Previous file is deleted
    to_delete_later.unlink()

    # Regular update
    w.incoming(create_new(dir_base / f"{_id}/Images", file_creator))
    assert "File bookkeeping inconsistency: files unexpectedly removed" in caplog.text


def test_ignore_setting_the_same_dir(dir_layout):
    dir_base, size, _id = dir_layout
    # same path for inferences and inferences do not count twice the files
    config = Persist(
        device_dir_path=str(dir_base),
        size="100",
        unit="MB",
    )
    w = StorageSizeWatcher(config, check_frequency=10)
    w.apply(config, _id)
    w.gather()

    assert w.content.size == size

    # Run gather() twice does not change anything
    w.gather()
    assert w.content.size == size


def test_incoming_always_prunes(dir_layout, file_creator):
    dir_base, _, _id = dir_layout
    mock_prune = Mock()
    with patch.object(StorageSizeWatcher, "_prune", mock_prune):
        conf = persist(base=dir_base, size=1)
        w = StorageSizeWatcher(conf, check_frequency=10)
        assert mock_prune.call_count == 0
        w.apply(conf, _id)
        w.gather()
        assert mock_prune.call_count == 1

        num_new_files = random.randint(5, 20)
        for _ in range(num_new_files):
            target = f"{_id}/" + random.choice(("Images", "Metadata"))
            w.incoming(create_new(dir_base / target, file_creator))
        assert mock_prune.call_count == num_new_files + 1


def test_remaining_before_consistency_check(dir_layout, file_creator):
    check_frequency = 10

    dir_base, _, _id = dir_layout
    mock_prune = Mock()
    with patch.object(StorageSizeWatcher, "_prune", mock_prune):
        conf = persist(base=dir_base, size=1)
        w = StorageSizeWatcher(conf, check_frequency=check_frequency)
        w.apply(conf, _id)
        w.gather()
        assert w._remaining_before_check == check_frequency

        for i in range(check_frequency):
            assert w._remaining_before_check == check_frequency - i
            target = f"{_id}/" + random.choice(("Images", "Metadata"))
            w.incoming(create_new(dir_base / target, file_creator))
        assert w._remaining_before_check == check_frequency


def test_age_bookkeeping():
    names = "abcdefghijklmn"
    timestamps = list(range(len(names)))
    random.shuffle(timestamps)

    # helper dict for building assertions
    min_timestamp = min(timestamps)
    max_timestamp = max(timestamps)
    helper = {
        timestamp: name
        for timestamp, name in zip(timestamps, names)
        if timestamp in (min_timestamp, max_timestamp)
    }
    name_of_min_timestamp = helper[min_timestamp]
    name_of_max_timestamp = helper[max_timestamp]

    odd = OrderedDict(
        sorted(
            ((((timestamp, name), None)) for timestamp, name in zip(timestamps, names)),
            key=lambda e: e[0],
        )
    )
    first_key = next(iter(odd.keys()))
    assert first_key == (min_timestamp, name_of_min_timestamp)

    last_key, _ = odd.popitem()
    assert last_key == (max_timestamp, name_of_max_timestamp)

    popped_first, _ = odd.popitem(last=False)
    assert first_key == popped_first


def test_regular_sequence_multiple_dirs(dir_layout, file_creator):
    dir_base, initial_size, _id = dir_layout
    expected_curr_size = initial_size
    conf = persist(size=initial_size / 1024)
    w = StorageSizeWatcher(conf, check_frequency=10)
    assert w.state == StorageSizeWatcher.State.Initialized

    conf.device_dir_path = dir_base
    w.apply(conf, _id)
    w.gather()
    assert w.state == StorageSizeWatcher.State.Accumulating
    assert w.content.size <= expected_curr_size
    oldest_age = w.content.older[0][2].age
    assert oldest_age == 0

    # Test that adding a new file with the set limit, does
    # invoke pruning, so the previous oldest file is removed.
    w.incoming(create_new(dir_base / f"{_id}/Metadata", file_creator))
    assert w.content.size == expected_curr_size
    oldest_age = w.content.older[0][2].age
    assert oldest_age == 1

    # Test creating and registering new files in lockstep
    num_new_files = random.randint(5, 20)
    for _, sub in zip(range(num_new_files), cycle(("Images", "Metadata"))):
        w.incoming(create_new(dir_base / f"{_id}/{sub}", file_creator))
        assert w._consistency_check()
        assert w.content.size <= initial_size

    files_created_up_to_now = initial_size / 1024 + 1 + num_new_files
    expected_newest_age = files_created_up_to_now - 1
    expected_oldest_age = expected_newest_age - 4 + 1
    oldest_age = w.content.older[0][2].age
    assert oldest_age == expected_oldest_age

    # Test setting a limit larger than current usage
    conf.size += 1024
    w.apply(conf, _id)
    w.gather()
    # expected_curr_size is unchanged as the limit
    # is greater than the current size.
    assert w.content.size == expected_curr_size


def test_ensure_dir_on_existing_dir(tmp_path_factory):
    existing = tmp_path_factory.mktemp("exists")
    # This assert checks out if no assertion was raised:
    assert check_and_create_directory(existing) is None

    assert existing.is_dir()


def test_ensure_dir_on_non_existing_dir(tmp_path_factory):
    base = tmp_path_factory.mktemp("base")
    assert base.is_dir()

    non_existing = base / "non_existent"
    assert not non_existing.is_dir()

    # This assert checks out if no assertion was raised:
    assert check_and_create_directory(non_existing) is None

    assert non_existing.is_dir()


def test_ensure_dir_on_file_path(tmp_path):
    a_file = tmp_path.joinpath("a_file")
    a_file.touch()
    with pytest.raises(UserException):
        check_and_create_directory(a_file)


@pytest.fixture
def observer() -> Iterator[Observer]:  # type: ignore
    obs = Observer()
    obs.start()
    yield obs
    obs.stop()
    with contextlib.suppress(RuntimeError):
        obs.join()


def test_simple_deletion_watch(observer, tmp_path):
    """
    This tests the simplest behavior emitting filesystem events
    on deletion, regardless whether it is files or directories.
    """

    fs_event = threading.Event()

    class EventHandler(FileSystemEventHandler):
        def on_deleted(self, event: FileSystemEvent) -> None:
            fs_event.set()

    dir_to_watch = tmp_path / "to_delete"
    dir_to_watch.mkdir()

    a_file = dir_to_watch / "a_file"
    a_file.touch()

    observer.schedule(EventHandler(), str(dir_to_watch))

    a_file.unlink()
    assert fs_event.wait()

    fs_event.clear()
    dir_to_watch.rmdir()
    assert fs_event.wait()


def test_directory_deletion_watch(observer, tmp_path):
    """
    This tests the simplest behavior emitting filesystem events
    on deletion, exclusively for directories.
    """

    fs_event = threading.Event()

    class EventHandler(FileSystemEventHandler):
        def on_deleted(self, event: FileSystemEvent) -> None:
            if event.is_directory:
                fs_event.set()

    dir_to_watch = tmp_path / "to_delete"
    dir_to_watch.mkdir()

    a_file = dir_to_watch / "a_file"
    a_file.touch()

    observer.schedule(
        # event_filter not supported on OSX
        EventHandler(),
        str(dir_to_watch),
    )

    a_file.unlink()
    assert not fs_event.wait(0.8)

    dir_to_watch.rmdir()
    assert fs_event.wait()


def test_online_watch_modification(observer, tmp_path):
    """
    This tests whether the observer object can have watches
    dynamically added and removed over its life time.
    """

    fs_event = threading.Event()

    class EventHandler(FileSystemEventHandler):
        def on_deleted(self, event: FileSystemEvent) -> None:
            if event.is_directory:
                fs_event.set()

    dir1_to_watch = tmp_path / "dir1"
    dir1_to_watch.mkdir()
    dir2_to_watch = tmp_path / "dir2"
    dir2_to_watch.mkdir()

    watch1 = observer.schedule(EventHandler(), str(dir1_to_watch))

    dir1_to_watch.rmdir()
    assert fs_event.wait()
    fs_event.clear()

    # Cannot "recycle" a watched location
    dir1_to_watch.mkdir()
    dir1_to_watch.rmdir()
    assert not fs_event.wait(1)
    observer.unschedule(watch1)

    watch2 = observer.schedule(EventHandler(), str(dir2_to_watch))
    dir2_to_watch.rmdir()
    assert fs_event.wait()

    observer.unschedule(watch2)


def test_directory_watcher(tmp_path):
    """
    This tests the DirectoryMonitor class
    """
    fs_event = threading.Event()

    def on_delete_cb(path: Path) -> None:
        fs_event.set()

    directory_monitor = DirectoryMonitor(on_delete_cb)
    directory_monitor.start()

    dir1_to_watch = tmp_path / "dir1"
    dir1_to_watch.mkdir()

    directory_monitor.watch(dir1_to_watch)
    dir1_to_watch.rmdir()
    assert fs_event.wait()

    with not_raises(KeyError):
        directory_monitor.unwatch(dir1_to_watch)

    directory_monitor.stop()


def test_regular_sequence_update_size(dir_layout, file_creator):
    dir_base, size, _id = dir_layout
    conf = persist(base=dir_base, size=size / 1024)
    w = StorageSizeWatcher(conf, check_frequency=10)
    w.apply(conf, _id)
    w.gather()
    assert w.content.size == size

    new_file = create_new(dir_base / f"{_id}/Images", file_creator)
    w.incoming(new_file)
    # Size must have remained constant
    assert w.content.size == size

    w.incoming(new_file)
    # Size must have remained constant
    assert w.content.size == size

    new_content = b"12345678"
    new_file.write_bytes(new_content)
    w.incoming(new_file)
    # This must have pushed an old 1 kB-sized file out
    assert w.content.size == (size - 1024) + len(new_content)


def test_size_unit_to_bytes():
    assert size_unit_to_bytes(1, UnitScale.KB) == 1024
    assert size_unit_to_bytes(1, UnitScale.MB) == 1024 * 1024
    assert size_unit_to_bytes(1, UnitScale.GB) == 1024 * 1024 * 1024


def _file(ref: int) -> FileInfo:
    return FileInfo(age=ref, path=f"/images/image{ref}.jpg", size=ref)


def test_container_pop_older() -> None:
    file1 = _file(1)
    file2 = _file(2)
    file3 = _file(3)
    container = FileInfoContainer()

    assert container.pop() is None

    assert container.add(file2) is None
    assert container.size == 2
    assert container.add(file3) is None
    assert container.size == 5
    assert container.add(file1) is None
    assert container.size == 6
    assert container.add(file2) is file2
    assert container.size == 6
    assert container.add(file1) is file1
    assert container.size == 6
    assert container.add(file3) is file3

    assert container.pop() == file1
    assert container.size == 5
    assert container.pop() == file2
    assert container.size == 3
    assert container.pop() == file3
    assert container.size == 0
    assert container.pop() is None
    assert container.size == 0


def test_container_same_path_keep_the_newest() -> None:
    same_path = "images/image.jpg"
    file1 = FileInfo(age=1, path=same_path, size=1)
    file2 = FileInfo(age=2, path=same_path, size=2)
    file3 = FileInfo(age=3, path=same_path, size=3)
    file4 = FileInfo(age=4, path=same_path, size=4)
    container = FileInfoContainer()

    assert container.add(file1) is None
    assert container.size == 1
    assert container.add(file2) is file1
    assert container.size == 2
    assert container.add(file4) is file2
    assert container.size == 4
    assert container.add(file3) is file3
    assert container.size == 4

    assert container.pop() == file4
    assert container.size == 0
    assert container.pop() is None
    assert container.size == 0


def test_addition_is_thread_safe() -> None:
    def add_some_files_files(thread_num: int, container: FileInfoContainer) -> None:
        for i in range(20):
            file = FileInfo(age=thread_num, path=f"/images/image{i}.jpg", size=1)
            container.add(file)
            time.sleep(0.01)

    container = FileInfoContainer()
    threads = []
    for i in range(50):
        thread = threading.Thread(
            target=add_some_files_files,
            args=(
                i,
                container,
            ),
        )
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    assert container.size == 20

    for i in range(20):
        older = container.pop()
        assert older.age == 49
        assert container.size == 19 - i


def test_relative_paths(tmp_path) -> None:
    _id = 1883
    curdir = os.curdir
    try:
        os.chdir(tmp_path)
        absolute_path = tmp_path / "subdir"
        absolute_path.mkdir()
        Config().update_persistent_attr(_id, "device_dir_path", absolute_path)

        relative_path = absolute_path.relative_to(tmp_path)
        conf = Persist(device_dir_path=relative_path, size=1, unit=UnitScale.KB)
        w = StorageSizeWatcher(conf)
        w.apply(conf, _id)
        w.gather()

        assert w.content.size == 0
        file = relative_path / f"{_id}/Metadata" / "file.txt"
        file.write_text("h" * 1024)

        w.incoming(file)
        assert w.content.size == 1024

        w.incoming(file.absolute())
        assert w.content.size == 1024

        w._consistency_check()
        assert w.content.size == 1024
    finally:
        os.chdir(curdir)
