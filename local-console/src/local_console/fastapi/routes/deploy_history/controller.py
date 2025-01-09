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
from local_console.core.deploy.deployment_manager import DeploymentManager
from local_console.core.deploy.tasks.base_task import Status
from local_console.core.deploy.tasks.base_task import Task
from local_console.core.deploy.tasks.config_task import ConfigTask
from local_console.core.deploy.tasks.task_executors import TaskEntity
from local_console.core.deploy.tasks.task_executors import TaskExecutor
from local_console.fastapi.pagination import Paginator
from local_console.fastapi.routes.deploy_history.dto import DeployHistory
from local_console.fastapi.routes.deploy_history.dto import DeployHistoryList


class DeployHistoryPaginator(Paginator):
    @classmethod
    def _get_element_key(cls, element: DeployHistory) -> str:
        return element.deploy_id


class DeployHistoryController:
    def __init__(
        self,
        tasks: TaskExecutor,
        deployment_manager: DeploymentManager,
        paginator: DeployHistoryPaginator = DeployHistoryPaginator(),
    ):
        self.__tasks = tasks
        self._deployment_manager = deployment_manager
        self.paginator = paginator

    def _sum(
        self, a: tuple[int, int, int], b: tuple[int, int, int]
    ) -> tuple[int, int, int]:
        """
        Sums two tuples of 3 elements.

        Examples:
        >>> add_numbers((1,1,1), (1,1,1))
        (2,2,2)
        """
        return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

    def _status_counter(self, task: Task) -> tuple[int, int, int]:
        """
        Counts the number of tasks with each status type (running, success, failed).
        This elements are used on DeployHistory response as (deploying_cnt,success_cnt,fail_cnt)
        """
        if isinstance(task, ConfigTask):
            result = (0, 0, 0)
            for subtask in task._tasks:
                result = self._sum(result, self._status_counter(subtask))
            return result
        else:
            if task.get_state() == Status.SUCCESS:
                return (0, 1, 0)
            elif task.get_state() == Status.ERROR:
                return (0, 0, 1)
            else:
                return (1, 0, 0)

    def _to_deploy_history(self, entity: TaskEntity) -> DeployHistory:
        statuses = self._status_counter(entity.task)
        history = DeployHistory(
            deploy_id=entity.id,
            from_datetime=entity.task.get_state().started_at,
            deploy_type=type(entity.task).__name__,
            deploying_cnt=statuses[0],
            success_cnt=statuses[1],
            fail_cnt=statuses[2],
        )
        if isinstance(entity.task, ConfigTask):
            config_deploy = entity.task.get_deploy_history_info()
            history.config_id = config_deploy.config_id
            history.edge_system_sw_package = config_deploy.edge_system_sw_package
            history.models = config_deploy.models
            history.edge_apps = config_deploy.edge_apps
        return history

    def get_list(
        self, limit: int = 10, starting_after: str | None = None
    ) -> DeployHistoryList:
        histories: list[DeployHistory] = []
        for task in self.__tasks.list():
            deploy_history = self._to_deploy_history(task)
            deploy_history.devices = (
                self._deployment_manager.get_device_history_for_deployment(
                    deploy_history.deploy_id
                )
            )
            histories.append(deploy_history)
        paginated, continuation = self.paginator.paginate(
            histories, limit, starting_after
        )
        return DeployHistoryList(
            deploy_history=paginated, continuation_token=continuation
        )
