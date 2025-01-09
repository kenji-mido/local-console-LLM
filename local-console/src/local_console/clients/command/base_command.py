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
from abc import ABC
from abc import abstractmethod
from typing import Generic
from typing import TypeVar

from local_console.core.schemas.schemas import OnWireProtocol
from pydantic import BaseModel


class CommandClient(ABC):

    @abstractmethod
    async def publish(self, topic: str, payload: str) -> None:
        raise NotImplementedError("Subclasses must implement this method")


class CommandArgument(BaseModel):
    onwire_schema: OnWireProtocol


class CommandResponse(BaseModel):
    pass


INPUT = TypeVar("INPUT", bound=CommandArgument)
OUTPUT = TypeVar("OUTPUT", bound=CommandResponse)


class MqttCommand(ABC, Generic[INPUT, OUTPUT]):
    def __init__(self, client: CommandClient) -> None:
        super().__init__()
        self.client = client

    @abstractmethod
    async def run(self, input: INPUT) -> OUTPUT:
        raise NotImplementedError("Subclasses must implement this method")
