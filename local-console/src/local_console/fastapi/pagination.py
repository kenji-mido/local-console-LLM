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
import abc
import logging
from abc import ABC
from typing import Any
from typing import TypeVar

from local_console.core.edge_apps import EdgeApp
from local_console.core.firmwares import Firmware

logger = logging.getLogger(__name__)

LIST_ITEM = TypeVar("LIST_ITEM")


class Paginator(ABC):
    def paginate(
        self,
        list_elements: list[LIST_ITEM],
        limit: int,
        continuation_token: str | None = None,
    ) -> tuple[list[LIST_ITEM], str | None]:
        continuation_index = self._pagination_index(list_elements, continuation_token)
        ending_index = continuation_index + limit
        paginated_elements = list_elements[continuation_index:ending_index]
        continuation_token = None
        if len(list_elements) > ending_index:
            continuation_token = self._get_element_key(list_elements[ending_index - 1])
        return paginated_elements, continuation_token

    @abc.abstractmethod
    def _get_element_key(self, element: Any) -> str: ...

    def _pagination_index(
        self, list_elements: list, continuation_token: str | None = None
    ) -> int:
        if continuation_token:
            for index, element in enumerate(list_elements):
                element_id = self._get_element_key(element)
                if element_id == continuation_token:
                    return index + 1
            logger.warning(f"invalid continuation token {continuation_token}")
        return 0


class EdgeAppsPaginator(Paginator):
    @classmethod
    def _get_element_key(cls, element: EdgeApp) -> str:
        return element.info.edge_app_package_id


class FirmwaresPaginator(Paginator):
    @classmethod
    def _get_element_key(cls, element: Firmware) -> str:
        return element.info.file_id
