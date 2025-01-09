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
from local_console.core.camera.schemas import DeviceStateInformation
from local_console.core.device_services import DeviceServices
from local_console.fastapi.routes.deploy_history.dto import DeviceDeployHistoryInfo


class DeploymentManager:
    """
    This manager handles the relationship between deployments and devices.
    It will track which devices have been assigned to which deployments.
    """

    def __init__(self, device_service: DeviceServices) -> None:
        # map `deploy_id` to list of `device_id`
        self._device_deployments: dict[str, set[int]] = {}
        self._device_service = device_service

    def add_device_to_deployment(self, deploy_id: str, device_id: int) -> None:
        self._device_deployments.setdefault(deploy_id, set()).add(device_id)

    def get_devices_for_deployment(self, deploy_id: str) -> list[int]:
        return list(self._device_deployments.get(deploy_id, []))

    def _device_dto_to_history(
        self, device_dto: DeviceStateInformation
    ) -> DeviceDeployHistoryInfo:
        return DeviceDeployHistoryInfo(
            device_id=device_dto.device_id, device_name=device_dto.device_name
        )

    def get_device_history_for_deployment(
        self, deploy_id: str
    ) -> list[DeviceDeployHistoryInfo]:
        """
        Get a list of device history information (DTOs) for a given deployment.
        This extends the manager to also interact with DevicesController to fetch device details.
        """
        device_ids = self.get_devices_for_deployment(deploy_id)
        return [
            self._device_dto_to_history(self._device_service.get_device(device_id))
            for device_id in device_ids
        ]
