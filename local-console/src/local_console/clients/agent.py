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
import random
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Optional

import paho.mqtt.client as paho
import trio
from local_console.clients.trio_paho_mqtt import AsyncClient
from paho.mqtt.client import MQTT_ERR_SUCCESS

logger = logging.getLogger(__name__)


class Agent:
    HOST = "localhost"

    def __init__(self, port: int) -> None:
        self.port = port

        self.client: Optional[AsyncClient] = None
        self.nursery: Optional[trio.Nursery] = None

        client_id = f"cli-client-{random.randint(0, 10**7)}"
        self.mqttc = paho.Client(clean_session=True, client_id=client_id)

    @asynccontextmanager
    async def mqtt_scope(self, subs_topics: list[str]) -> AsyncIterator[None]:
        is_os_error = False  # Determines if an OSError occurred within the context

        try:
            async with trio.open_nursery() as nursery:

                self.nursery = nursery
                self.client = AsyncClient(self.mqttc, self.nursery)
                try:
                    self.client.connect(Agent.HOST, self.port)
                    for topic in subs_topics:
                        self.client.subscribe(topic)
                    yield
                except OSError:
                    logger.error(
                        f"Error while connecting to MQTT broker {Agent.HOST}:{self.port}"
                    )
                    is_os_error = True
                finally:
                    self.client.disconnect()
                    self.nursery.cancel_scope.cancel()

        except* Exception as excgroup:
            for e in excgroup.exceptions:
                logger.exception(
                    "Exception occurred within MQTT client processing:", exc_info=e
                )
            is_os_error = True

        if is_os_error:
            raise SystemExit

    async def publish(self, topic: str, payload: str) -> None:
        assert self.client is not None
        msg_info = await self.client.publish_and_wait(topic, payload=payload)
        if msg_info[0] != MQTT_ERR_SUCCESS:
            logger.error("Error on MQTT publish agent logs")
            raise ConnectionError
