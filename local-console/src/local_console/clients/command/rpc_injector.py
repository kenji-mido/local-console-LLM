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

from local_console.clients.command.rpc_base import RPCArgument
from local_console.core.schemas.edge_cloud_if_v1 import StartUploadInferenceData


class RPCInjector(ABC):
    @abstractmethod
    def inject(self, input: RPCArgument) -> RPCArgument: ...


class StartStreamingProvider(ABC):
    @abstractmethod
    def streaming_rpc_start_content(self) -> StartUploadInferenceData: ...


class StartStreamingInjector(RPCInjector):
    def __init__(self, camera_state: StartStreamingProvider) -> None:
        self._camera_state = camera_state

    def inject(self, input: RPCArgument) -> RPCArgument:
        if input.method == "StartUploadInferenceData":
            defaults = self._camera_state.streaming_rpc_start_content()
            input.params.update(
                {
                    k: v
                    for k, v in defaults.model_dump().items()
                    if k not in input.params
                }
            )
        return input


class ChainedRPCInjector(RPCInjector):
    def __init__(self, injectors: list[RPCInjector]) -> None:
        self._injectors = injectors

    def inject(self, input: RPCArgument) -> RPCArgument:
        enriched = input
        for injector in self._injectors:
            enriched = injector.inject(enriched)
        return enriched


def empty_injector() -> RPCInjector:
    return ChainedRPCInjector([])
