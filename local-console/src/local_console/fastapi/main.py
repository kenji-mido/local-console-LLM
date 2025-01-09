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
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import trio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from local_console.core.config import config_obj
from local_console.fastapi.dependencies.commons import added_file_manager
from local_console.fastapi.dependencies.commons import running_background_task
from local_console.fastapi.dependencies.commons import stop_background_task
from local_console.fastapi.dependencies.devices import add_device_service
from local_console.fastapi.dependencies.devices import device_service_from_app
from local_console.fastapi.error_handler import handle_all_exceptions
from local_console.fastapi.middleware.log_all_requests import LogAllRequestMiddleware
from local_console.fastapi.routes import edge_apps
from local_console.fastapi.routes import files
from local_console.fastapi.routes import firmwares
from local_console.fastapi.routes import models
from local_console.fastapi.routes import provisioning
from local_console.fastapi.routes.deploy_configs import router as deploy_configs
from local_console.fastapi.routes.deploy_history import router as deploy_history
from local_console.fastapi.routes.devices import router as devices
from local_console.fastapi.routes.health import router as health
from local_console.fastapi.routes.images import router as images
from local_console.fastapi.routes.inferenceresults import router as inferenceresults

logger = logging.getLogger(__name__)


def app_router(app: FastAPI) -> None:
    app.include_router(provisioning.router)
    app.include_router(devices.router)
    app.include_router(files.router)
    app.include_router(firmwares.router)
    app.include_router(models.router)
    app.include_router(edge_apps.router)
    app.include_router(deploy_configs.router)
    app.include_router(deploy_history.router)
    app.include_router(images.router)
    app.include_router(inferenceresults.router)
    app.include_router(health.router)


def enable_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8000", "http://localhost:4200"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    devices = config_obj.get_device_configs()
    async with trio.open_nursery() as nursery, running_background_task(app):
        with added_file_manager(app):
            add_device_service(app, nursery)
            ds = device_service_from_app(app)
            ds.init_devices(devices)
            yield

        logger.debug("Entering shutdown phase")
        ds.shutdown()
        await stop_background_task(app)
        # FIXME: Some tasks remain running and nursery gets blocked
        nursery.cancel_scope.cancel()


def generate_server() -> FastAPI:
    app = FastAPI(title="Local console Web UI", lifespan=lifespan)
    app_router(app)
    handle_all_exceptions(app)
    enable_cors(app)
    app.add_middleware(LogAllRequestMiddleware)
    return app
