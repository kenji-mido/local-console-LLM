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
import enum
import heapq
import logging
import os
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from local_console.core.camera.enums import UnitScale
from local_console.core.camera.streaming import image_dir_for
from local_console.core.camera.streaming import inference_dir_for
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes
from local_console.core.schemas.schemas import DeviceID
from local_console.core.schemas.schemas import Persist
from watchdog.events import DirDeletedEvent
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import ObservedWatch

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    age: int
    path: Path
    size: int


class WatchException(Exception):
    pass


def size_unit_to_bytes(size: int, unit: UnitScale) -> int:
    factors = {UnitScale.KB: 2**10, UnitScale.MB: 2**20, UnitScale.GB: 2**30}
    return size * factors[unit]


class FileInfoContainer:
    def __init__(self) -> None:
        self.unique: dict[Path, FileInfo] = {}
        self.older: list[tuple[int, int, FileInfo]] = []
        self.older_id = 0
        self.size = 0
        self.lock = threading.Lock()

    def _accept(self, file: FileInfo) -> None:
        heapq.heappush(self.older, (file.age, self.older_id, file))
        self.unique[file.path] = file
        self.older_id += 1
        self.size += file.size

    def _discard(self) -> FileInfo:
        _, _, older = heapq.heappop(self.older)
        del self.unique[older.path]
        self.size -= older.size
        return older

    def _replace_by_newer(self, new: FileInfo) -> None:
        temporal: list[FileInfo] = []
        while self.older:
            curr = self._discard()
            if curr.path == new.path:
                self._accept(new)
                for missing in temporal:
                    self._accept(missing)
                return
            else:
                temporal.append(curr)

    def _resolve_duplicate(self, prev: FileInfo, new: FileInfo) -> FileInfo:
        if prev.age < new.age:
            logger.error(
                f"File {new.path} already registered. It will be replaced as new file age is {new.age} and previous is {prev.age}"
            )
            self._replace_by_newer(new)
            return prev
        else:
            logger.error(
                f"File {new.path} duplicated. But is ignored as is not newer than {prev.age}"
            )
            return new

    def add(self, file: FileInfo) -> FileInfo | None:
        """
        Add file and return the discarded one if duplicated
        """
        with self.lock:
            prev = self.unique.get(file.path)
            if prev is None:
                self._accept(file)
                return None
            else:
                older = self._resolve_duplicate(prev, file)
                return older

    def pop(self) -> FileInfo | None:
        """
        Remove the older from container and returns it. But returns None if empty
        """
        with self.lock:
            try:
                older = self._discard()
                return older
            except IndexError:
                return None

    def paths(self) -> set[Path]:
        return {f.path for f in self.unique.values()}

    def clear(self) -> None:
        self.older.clear()
        self.unique.clear()
        self.size = 0


OnDeleteCallable = Callable[[Path], None]


class StorageSizeWatcher:
    class State(enum.Enum):
        Initialized = enum.auto()
        Configured = enum.auto()
        Accumulating = enum.auto()
        Checking = enum.auto()

    def __init__(
        self,
        config: Persist,
        check_frequency: int = 50,
        on_delete_cb: OnDeleteCallable = lambda dir: None,
    ) -> None:
        """
        Class for watching a directory for incoming files while maintaining
        the total storage usage within the directory under a given limit size,
        pruning the oldest files when necessary.

        Bookkeeping is made in-memory for it to remain fast, however consistency
        is checked against the filesystem once every given number of incoming
        files.

        Args:
                config: (Persist) size limit settings ('unit' and 'size' must be set)
                check_frequency (int, optional): check consistency after this many new files. Defaults to 50.
        """
        assert isinstance(config.size, int)
        assert config.unit

        self._paths: set[Path] = set()
        self._size_limit = size_unit_to_bytes(config.size, config.unit)
        self.check_frequency = check_frequency
        self.content = FileInfoContainer()
        self._remaining_before_check = self.check_frequency
        self.monitor = DirectoryMonitor(on_delete_cb)
        self.state = self.State.Initialized

    def apply(self, config: Persist, device_id: DeviceID) -> None:
        assert isinstance(config.size, int)
        assert config.unit

        for path in self._paths:
            self.monitor.unwatch(path)
        self._paths.clear()
        self._size_limit = size_unit_to_bytes(config.size, config.unit)

        if config.device_dir_path:
            image_dir = image_dir_for(device_id, config.device_dir_path)
            assert image_dir
            self._set_path(image_dir)

            inference_dir = inference_dir_for(device_id, config.device_dir_path)
            assert inference_dir
            self._set_path(inference_dir)

        self.state = self.State.Configured
        logger.debug("New configuration applied to storage size watcher")

    def gather(self, prune_enabled: bool = True) -> None:
        self._consistency_check()
        if prune_enabled:
            self._prune()
        self.state = self.State.Accumulating

    def _set_path(self, path: Path) -> None:
        check_and_create_directory(path)

        p = path.resolve()
        if p in self._paths:
            return

        logger.debug(f"Including path {p} in size limiting watchlist.")
        self._paths.add(p)
        self.monitor.watch(path)

    def incoming(self, path: Path, prune_enabled: bool = True) -> None:
        assert path.is_file()

        if not self._paths:
            return

        if not any(path.resolve().is_relative_to(root) for root in self._paths):
            raise WatchException(
                f"Incoming file {path} does not belong to either of {self._paths}"
            )

        # If necessary, perform the required state transition
        if self.state == self.State.Configured:
            self.gather(prune_enabled)

        # Steady-state operation occurs in Accumulating state
        if self.state == self.State.Accumulating:
            self._register_file(path)

            self._remaining_before_check -= 1
            if self._remaining_before_check <= 0:
                self._consistency_check()
                self._remaining_before_check = self.check_frequency

            if prune_enabled:
                self._prune()
        else:
            logger.warning(
                f"Deferring update of size statistic for incoming file {path} during state {self.state}"
            )

    def size(self) -> int:
        # NOTE: consider performance
        self._consistency_check()
        return self.content.size

    @property
    def current_limit(self) -> int:
        return self._size_limit

    def can_accept(self) -> bool:
        """
        Checks if the current storage content size is within the allowed limit.
        """
        return self.content.size <= self._size_limit

    def start(self) -> None:
        self.monitor.start()

    def stop(self) -> None:
        self.monitor.stop()

    def _register_file(self, path: Path) -> None:
        entry = walk_entry(path)
        logger.debug(f"Registering for size limiting: {entry}")

        self.content.add(entry)

    def _prune(self) -> None:
        # In order to make this class thread-safe,
        # the following would be required:
        # self.state == self.State.Checking
        has_been_pruned = False
        while self.content.size > self._size_limit:
            try:
                entry = self.content.pop()
                if not entry:
                    logger.error(
                        "There are no more files in the content, but the usage limits have been exceeded."
                    )
                    self._consistency_check()
                    return
                path = entry.path
                path.unlink()
                has_been_pruned = True
                logger.debug(f"Removed {path} for pruning, freed {entry.size} bytes")
            except FileNotFoundError as e:
                logger.warning(f"File {path} was already removed", exc_info=e)
            except Exception as e:
                logger.warning("Unexpected exception while pruning", exc_info=e)

        if has_been_pruned:
            logger.debug(
                f"Prune has been applied. Current storage usage is {self.content.size}"
            )
        # In order to make this class thread-safe,
        # the following would be required:
        # self.state == self.State.Accumulating

    def _consistency_check(self) -> bool:
        in_memory = self.content.paths()
        valid_paths = (root for root in self._paths if root.is_dir())
        files_in_paths = [p for root in valid_paths for p in walk_files(root)]
        in_storage = {p.path for p in files_in_paths}

        missing_in_memory = in_storage - in_memory
        orphaned_in_memory = in_memory - in_storage
        if missing_in_memory or orphaned_in_memory:
            if missing_in_memory:
                logger.warning(
                    f"File bookkeeping inconsistency: new files on disk are: {missing_in_memory}"
                )
            if orphaned_in_memory:
                logger.warning(
                    f"File bookkeeping inconsistency: files unexpectedly removed: {orphaned_in_memory}"
                )
            self.content.clear()
            for file in files_in_paths:
                self.content.add(file)
            return False

        return True


def entry_from_stats(path: Path, stats: os.stat_result) -> FileInfo:
    file_age = stats.st_mtime_ns
    file_size = stats.st_size
    return FileInfo(file_age, path, file_size)


def walk_entry(path: Path) -> FileInfo:
    path = path.resolve()
    return entry_from_stats(path, os.stat(path))


def walk_files(root: Path) -> Iterator[FileInfo]:
    # Use os.scandir, https://peps.python.org/pep-0471/, to improve performance by getting stats
    # without additional system calls in most of the cases
    for entry in os.scandir(root):
        if entry.is_file():
            stat = (
                entry.stat()
            )  # do not remove From https://peps.python.org/pep-0471, stat(*, follow_symlinks=True): like os.stat(), but the return value is cached on the DirEntry
            yield entry_from_stats(Path(entry.path), stat)
        elif entry.is_dir():
            yield from walk_files(Path(entry.path))


def folders_setup_validation(selected_dir: Path) -> None:

    # Cross-platform file write smoke test
    test_f = selected_dir / "__lctestfile"
    test_f.write_text("1")
    test_f.unlink()


def check_and_create_directory(directory: Path) -> None:
    try:
        if not directory.exists():
            logger.warning(f"{directory} does not exist. Creating directory...")
            directory.mkdir(exist_ok=True, parents=True)

        assert directory.is_dir()
        folders_setup_validation(directory)
    except Exception as e:
        raise UserException(
            code=ErrorCodes.EXTERNAL_CANNOT_USE_DIRECTORY,
            # FIXME improve this
            message=str(e),
        )


class DirectoryMonitor:

    class EventHandler(FileSystemEventHandler):
        def __init__(self, on_delete_cb: OnDeleteCallable) -> None:
            self._on_delete_cb = on_delete_cb

        def on_deleted(self, event: DirDeletedEvent) -> None:
            if event.is_directory:
                self._on_delete_cb(event)

    def __init__(self, on_delete_cb: OnDeleteCallable = lambda dir: None) -> None:
        self._obs = Observer()
        self._watches: dict[Path, ObservedWatch] = dict()
        self.on_delete_cb = on_delete_cb

    def start(self) -> None:
        self._obs.start()

    def watch(self, directory: Path) -> None:
        assert directory.is_dir()
        resolved = directory.resolve()
        handler = self.EventHandler(self._watch_decorator(self.on_delete_cb))
        watch = self._obs.schedule(
            handler,
            str(resolved),
        )
        self._watches[resolved] = watch

    def _on_delete_action(self, path: Path) -> None:
        resolved = path.resolve()
        watch = self._watches.pop(resolved)
        self._obs.unschedule(watch)

    def _watch_decorator(self, on_delete_cb: OnDeleteCallable) -> Callable:

        def complete_callback(event: DirDeletedEvent) -> None:
            path = Path(event.src_path)
            self._on_delete_action(path)
            on_delete_cb(path)

        return complete_callback

    def unwatch(self, directory: Path) -> None:
        try:
            self._on_delete_action(directory)
        except KeyError:
            pass

    def stop(self) -> None:
        self._obs.stop()
        with contextlib.suppress(RuntimeError):
            self._obs.join()
