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
# This environment variable can be used to influence where will
# image and inference directories be created by default
import logging
import os
from pathlib import Path

import platformdirs
from local_console.core.config import Config
from local_console.core.schemas.schemas import DeviceID

logger = logging.getLogger(__name__)

ENV_DEFAULT_DIRS_PATH = "LC_DEFAULT_DIRS_PATH"


def get_default_files_dir() -> Path:
    default_dir = os.getenv(ENV_DEFAULT_DIRS_PATH, platformdirs.user_documents_dir())
    logger.debug(f"Will create data directories under {default_dir} by default")
    return Path(default_dir)


def get_default_device_dir_path() -> Path:
    return get_default_files_dir() / "local-console"


def setup_device_dir_path(device_id: DeviceID) -> Path:
    default_dir_base = get_default_device_dir_path()
    default_dir_base.mkdir(parents=True, exist_ok=True)
    Config().update_persistent_attr(device_id, "device_dir_path", default_dir_base)
    return default_dir_base
