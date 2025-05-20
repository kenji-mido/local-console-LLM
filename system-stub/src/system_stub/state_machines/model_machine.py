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
import threading
import time
from pathlib import PosixPath

import requests
from mocked_device.mock_v2.ai_model_message import DeployAiModel
from mocked_device.mock_v2.ai_model_message import ProcessStateEnum
from mocked_device.mock_v2.ai_model_message import ResInfo
from mocked_device.mock_v2.ai_model_message import ResultCodeEnum
from mocked_device.mock_v2.device_v2 import MockDeviceV2
from mocked_device.mock_v2.state_machines.model_machine import ModelMachineV2


logger = logging.getLogger(__name__)

# Path to the IMX500 neural network model used by SensCord.
#
# SensCord is configured via the XML file located at:
# /opt/senscord/share/senscord/config/senscord.xml
#
# This XML file references a post-processing configuration file:
# /opt/senscord/share/rpi-camera-assets/custom.json
#
# The `custom.json` configuration file includes the model path, which must match
# `SENSCORD_IMX500_MODEL_PATH`.
#
# Note:
# The model is not loaded directly via Picamera2.
# Instead, SensCord handles the loading and inference of the model when the Edge App
# transitions to the "Running" state.
SENSCORD_IMX500_MODEL_PATH = "/opt/senscord/share/imx500-models/network.rpk"


class ModelLoader:

    def load_model(self, package_url: str) -> None:
        logger.info("Loading model...")
        if not package_url.endswith(".rpk"):
            raise Exception("Only RPK models are supported.")
        response = requests.get(package_url)
        file = PosixPath(SENSCORD_IMX500_MODEL_PATH).expanduser()
        logger.debug(f"Saving file at {file}")
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(response.content)
        logger.info("Model loaded.")


class ModelMachineRpi(ModelMachineV2):
    def __init__(self, device: MockDeviceV2) -> None:
        self._device = device
        self.model_loader = ModelLoader()
        self._pending_events: list[DeployAiModel] = []
        self._thread: threading.Thread = threading.Thread(target=self.start)
        self._thread.start()

    def new_event(self, config: DeployAiModel) -> None:
        self._pending_events.append(config)

    def _process_event(self, config: DeployAiModel) -> None:
        logger.info(f"New AI model event: {config}")
        self._device.status.system_ai_model_deployment.req_info = config.req_info
        self._device.status.system_ai_model_deployment.res_info = ResInfo(
            res_id=config.req_info.req_id, code=ResultCodeEnum.ok, detail_msg="ok"
        )

        assert len(config.targets) <= 1

        for target in config.targets:
            # NOTE: intermediate states ('request_received', 'downloading', 'installing') are skipped
            # This is a simplification. Local Console waits for progress=100 and process_state="done"
            target.process_state = ProcessStateEnum.done
            target.progress = 100
            assert target.package_url
            try:
                self.model_loader.load_model(target.package_url)
            except Exception as e:
                logger.warning("Setting process_state to failed.", exc_info=e)
                self._device.status.system_ai_model_deployment.res_info.code = (
                    ResultCodeEnum.failed_precondition
                )
                target.process_state = ProcessStateEnum.failed
        self._device.status.system_ai_model_deployment.targets = config.targets

        self._device.send_status()

    def start(self) -> None:
        while True:
            while len(self._pending_events) > 0:
                next_event = self._pending_events.pop(0)
                logger.debug("Processing new model event")
                self._process_event(next_event)
            time.sleep(0.1)
