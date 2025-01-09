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
from collections.abc import AsyncGenerator
from collections.abc import Generator
from contextlib import asynccontextmanager
from contextlib import contextmanager
from typing import Annotated

from fastapi import Depends
from fastapi import FastAPI
from fastapi import Request
from local_console.core.config import Config
from local_console.core.config import config_obj
from local_console.core.deploy.tasks.task_executors import TrioBackgroundTasks
from local_console.core.files.files import FilesManager
from local_console.core.files.files import temporary_files_manager


def global_config() -> Config:
    return config_obj


@contextmanager
def added_file_manager(app: FastAPI) -> Generator[None, None, None]:
    with temporary_files_manager() as file_manager:
        if not hasattr(app.state, "file_manager"):
            app.state.file_manager = file_manager
        yield


def file_manager(request: Request) -> FilesManager:
    app = request.app
    assert isinstance(app.state.file_manager, FilesManager)
    return app.state.file_manager


@asynccontextmanager
async def running_background_task(
    app: FastAPI,
) -> AsyncGenerator[TrioBackgroundTasks, None]:
    async with TrioBackgroundTasks().run_forever() as bg:
        app.state.deploy_background_task = bg
        yield bg


async def stop_background_task(app: FastAPI) -> None:
    bg: TrioBackgroundTasks = app.state.deploy_background_task
    await bg.stop()


def deploy_background_task(request: Request) -> TrioBackgroundTasks:
    assert isinstance(request.app.state.deploy_background_task, TrioBackgroundTasks)
    return request.app.state.deploy_background_task


InjectGlobalConfig = Annotated[Config, Depends(global_config)]

InjectFilesManager = Annotated[FilesManager, Depends(file_manager)]

InjectDeployBackgroundTask = Annotated[
    TrioBackgroundTasks, Depends(deploy_background_task)
]
