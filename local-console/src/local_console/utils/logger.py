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
import logging
from datetime import datetime
from datetime import timezone

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s"


def custom_formatTime(
    self: logging.Formatter, record: logging.LogRecord, datefmt: str | None = None
) -> str:
    # See https://docs.python.org/3/library/logging.html#logging.Formatter.formatTime
    return datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()


def configure_logger(silent: bool, verbose: bool) -> None:
    level = logging.INFO
    if verbose:
        level = logging.DEBUG
    if silent:
        level = logging.WARNING

    logging.basicConfig(format=LOG_FORMAT, level=level)
    setattr(logging.Formatter, "formatTime", custom_formatTime)

    logging.getLogger("watchdog.observers").setLevel(logging.WARNING)
