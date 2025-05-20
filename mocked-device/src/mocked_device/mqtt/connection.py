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
import time
from typing import Any

import paho.mqtt.client as mqtt
from mocked_device.mqtt.event import TopicListener
from mocked_device.mqtt.router import MessageRouter
from mocked_device.mqtt.values import MqttConfig
from mocked_device.mqtt.values import TargetedMqttMessage
from mocked_device.utils.timeout import EVENT_WAITING_2S

logger = logging.getLogger(__name__)


class MqttConnection:
    def __init__(self, config: MqttConfig, router: MessageRouter):
        self.config = config
        self._router = router
        self._client: mqtt.Client = self._create_client(config)
        self.is_connected = False
        self.is_reconnected = False
        self._backup_listeners: list[TopicListener] = []

    def _on_connect(
        self, client: mqtt.Client, userdata: Any, flags: Any, rc: int
    ) -> None:
        self.is_connected = True
        if self.is_reconnected:
            for listener in self._backup_listeners:
                self.add_listener(listener)

    def _on_message(
        self, _client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage
    ) -> None:
        self._router.route(
            TargetedMqttMessage(
                config=self.config, topic=msg.topic, payload=msg.payload
            )
        )

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        for listener in self._backup_listeners:
            self.remove_listener(listener)

        self.is_connected = False
        logger.info("Client disconnected")
        while not self.is_connected:
            try:
                if self._client.reconnect() == 0:
                    self.is_connected = True
                    self.is_reconnected = True
            except:
                logger.info("Reconnection unsuccessful, trying again")
                time.sleep(1)
        logger.info("Reconnection successful!")

    def _create_client(self, config: MqttConfig) -> mqtt.Client:
        client = mqtt.Client()
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect
        client.connect(host=self.config.host, port=self.config.port)
        return client

    def remove_listener(self, listener: TopicListener) -> None:
        self._client.unsubscribe(listener.filter.topic())
        self._router.remove_handler(listener)

    def add_listener(self, listener: TopicListener) -> None:
        self._client.subscribe(listener.filter.topic())
        self._router.add_handler(listener)

        if listener not in self._backup_listeners:
            logger.info("Adding backup")
            self._backup_listeners.append(listener)

    def start(self) -> None:
        self._client.loop_start()
        EVENT_WAITING_2S.wait_for(lambda: self.is_connected)
        if not self.is_connected:
            raise Exception(f"Could not connect to {self.config.port}")

    def stop(self) -> None:
        self._client.loop_stop()

    def publish(self, message: TargetedMqttMessage) -> None:
        if self.is_connected:
            assert message.config == self.config
            result = self._client.publish(message.topic, message.payload, qos=1)
            if result.rc != 0:
                logger.error(
                    f"Could not send message to server {self.config.port} result value is {result.rc}"
                )
        else:
            logger.warning("Client disconnected. Not possible to send messages")


def create_connection(config: MqttConfig) -> MqttConnection:
    router = MessageRouter()
    mqtt_connection = MqttConnection(config, router)
    mqtt_connection.start()
    return mqtt_connection
