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

import trio
from local_console.core.camera.schemas import PropertiesReport
from local_console.core.camera.states.base import BaseStateProperties
from local_console.core.camera.states.base import MQTTDriver
from local_console.core.camera.states.base import StateWithProperties
from local_console.core.config import Config
from local_console.core.enums import DEFAULT_PERSIST_SETTINGS
from local_console.core.schemas.schemas import DeviceConnection
from local_console.core.schemas.schemas import DeviceID
from local_console.core.schemas.schemas import DeviceType
from local_console.servers.webserver import AsyncWebserver
from local_console.servers.webserver import FileInbox
from local_console.utils.fstools import StorageSizeWatcher


def find_device_config(name: str | None, port: int | None) -> DeviceConnection:
    config_obj = Config()
    if name:
        return config_obj.get_device_config_by_name(name)
    if port:
        return config_obj.get_device_config(DeviceID(port))
    return config_obj.get_first_device_config()


def dummy_props_for_state(config: DeviceConnection) -> BaseStateProperties:

    webserver = AsyncWebserver(port=Config().data.config.webserver.port)

    return BaseStateProperties(
        id=config.id,
        mqtt_drv=MQTTDriver(config),
        webserver=webserver,
        file_inbox=FileInbox(webserver),
        transition_fn=dummy_transition,
        trio_token=trio.lowlevel.current_trio_token(),
        message_send_channel=trio.open_memory_channel(0)[0],
        dirs_watcher=StorageSizeWatcher(
            DEFAULT_PERSIST_SETTINGS.model_copy(),
            on_delete_cb=dummy_notify_directory_deleted,
        ),
        device_type=DeviceType.UNKNOWN,
        reported=PropertiesReport(),
        on_report_fn=dummy_report_fn,
    )


async def dummy_transition(state: StateWithProperties) -> None:
    """
    No state transition is to be done in commands
    """


def dummy_report_fn(dev_id: DeviceID, report: PropertiesReport) -> None:
    """
    No need to react to data reports to device
    """


def dummy_notify_directory_deleted(dir_path: Path) -> None:
    """
    No need to react to data reports to device
    """
