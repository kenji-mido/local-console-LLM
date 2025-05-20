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

from mocked_device.mock_v2.ai_model_message import DeployAiModel
from mocked_device.mock_v2.ai_model_message import ProcessStateEnum
from mocked_device.mock_v2.ai_model_message import ResInfo
from mocked_device.mock_v2.ai_model_message import ResultCodeEnum
from mocked_device.mock_v2.device_v2 import MockDeviceV2
from mocked_device.mock_v2.message import AiModel
from mocked_device.utils.timing import now

logger = logging.getLogger(__name__)

MODEL_FAILURE_MARKER = "model_fail"


class ModelMachineV2:
    def __init__(self, device: MockDeviceV2) -> None:
        self._device = device
        self._pending_events: list[DeployAiModel] = []
        self._thread: threading.Thread = threading.Thread(target=self.start)
        self._thread.start()

    def new_event(self, config: DeployAiModel) -> None:
        self._pending_events.append(config)

    def _send_failure(self, config: DeployAiModel) -> None:
        logger.debug("Failing model deployment")
        self._device.status.system_ai_model_deployment.req_info = config.req_info
        self._device.status.system_ai_model_deployment.targets = config.targets
        self._device.status.system_ai_model_deployment.res_info = ResInfo(
            res_id=config.req_info.req_id, code=ResultCodeEnum.ok, detail_msg="ok"
        )

        self._device.status.system_ai_model_deployment.targets[0].process_state = (
            ProcessStateEnum.request_received
        )
        self._device.status.system_ai_model_deployment.targets[0].progress = 0
        self._device.send_status()

        self._device.status.system_ai_model_deployment.res_info = ResInfo(
            res_id=config.req_info.req_id,
            code=ResultCodeEnum.unavailable,
            detail_msg="unavailable",
        )
        self._device.status.system_ai_model_deployment.targets[0].process_state = (
            ProcessStateEnum.failed
        )
        self._device.status.system_ai_model_deployment.targets[0].progress = 0
        self._device.send_status()
        logger.debug("Model deployment failed")

    def _send_delete(self, config: DeployAiModel) -> None:
        logger.debug("Deleting model")
        self._device.status.system_ai_model_deployment.req_info = config.req_info
        self._device.status.system_ai_model_deployment.res_info = ResInfo(
            res_id=config.req_info.req_id, code=ResultCodeEnum.ok, detail_msg="ok"
        )
        self._device.status.system_ai_model_deployment.targets = config.targets
        # Sensor chip is the second one in the chips list
        self._device.status.system_device_info.chips[1].ai_models[0] = AiModel(
            version="",
            hash="",
            update_date="",
        )
        self._device.send_status()

        logger.debug("Model deleted")

    def _send_status(self, config: DeployAiModel) -> None:
        logger.debug("Deploying model")
        self._device.status.system_ai_model_deployment.req_info = config.req_info
        self._device.status.system_ai_model_deployment.targets = config.targets
        self._device.status.system_ai_model_deployment.res_info = ResInfo(
            res_id=config.req_info.req_id, code=ResultCodeEnum.ok, detail_msg="ok"
        )
        states = [
            ProcessStateEnum.request_received,
            ProcessStateEnum.downloading,
            ProcessStateEnum.downloading,
            ProcessStateEnum.installing,
            ProcessStateEnum.done,
        ]

        progress_values = [0, 25, 50, 75, 100]

        for state, progress in zip(states, progress_values):
            self._device.status.system_ai_model_deployment.targets[0].process_state = (
                state
            )
            self._device.status.system_ai_model_deployment.targets[0].progress = (
                progress
            )
            if progress == 100:
                # Sensor chip is the second one in the chips list
                self._device.status.system_device_info.chips[1].ai_models[0] = AiModel(
                    version=config.targets[0].version,  # type: ignore [arg-type]
                    hash=config.targets[0].hash,  # type: ignore [arg-type]
                    update_date=now().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                )
            self._device.send_status()
        logger.debug("Model deployed")

    def _process_event(self, config: DeployAiModel) -> None:
        if len(config.targets) == 0:
            self._send_delete(config)
        else:
            assert config.targets[0].package_url
            if MODEL_FAILURE_MARKER in config.targets[0].package_url:
                self._send_failure(config)
            else:
                self._send_status(config)

    def start(self) -> None:
        while True:
            while len(self._pending_events) > 0:
                next_event = self._pending_events.pop(0)
                logger.debug("Processing new model event")
                self._process_event(next_event)
            time.sleep(0.1)
