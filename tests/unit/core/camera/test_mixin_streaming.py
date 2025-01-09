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
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

from local_console.core.camera.mixin_streaming import StreamingMixin


def test_input_directory_setup_same_paths():
    mixin = StreamingMixin()

    mixin.total_dir_watcher = MagicMock()
    mixin.dir_monitor = MagicMock()

    current_and_previous = "/path/to/dir"

    mixin.input_directory_setup(current_and_previous, current_and_previous)

    mixin.total_dir_watcher.set_path.assert_not_called()
    mixin.dir_monitor.watch.assert_not_called()
    mixin.total_dir_watcher.unwatch_path.assert_not_called()
    mixin.dir_monitor.unwatch.assert_not_called()


def test_input_directory_setup_change_paths():
    mixin = StreamingMixin()

    mixin.total_dir_watcher = MagicMock()
    mixin.dir_monitor = MagicMock()
    mixin.notify_directory_deleted = MagicMock()

    with (
        patch(
            "local_console.core.camera.mixin_streaming.check_and_create_directory"
        ) as mock_check_create_dir,
        patch(
            "local_console.core.camera.mixin_streaming.folders_setup_validation"
        ) as mock_folders_validation,
    ):
        current = Path("/path/to/new_dir")
        previous = Path("/path/to/old_dir")

        mixin.input_directory_setup(str(current), str(previous))

        # verifications for current path
        mock_check_create_dir.assert_called_once_with(current)
        mock_folders_validation.assert_called_once_with(current)
        mixin.total_dir_watcher.set_path.assert_called_once_with(current)
        mixin.dir_monitor.watch.assert_called_once_with(
            current, mixin.notify_directory_deleted
        )

        # verifications for previous path
        mixin.total_dir_watcher.unwatch_path.assert_called_once_with(previous)
        mixin.dir_monitor.unwatch.assert_called_once_with(previous)
