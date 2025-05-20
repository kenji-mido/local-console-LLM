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
import argparse
import logging

from mocked_device.device import MockDevice
from mocked_device.listeners.image import ImageListener
from mocked_device.mqtt.connection import create_connection
from mocked_device.mqtt.event import TopicListener
from mocked_device.mqtt.values import MqttConfig
from mocked_device.retry.retrier import Retry
from system_stub.device_rpi import MockDeviceRPI
from system_stub.listeners.model import ModelListenerRpi

LOG_FORMAT = "%(asctime)s [%(threadName)s][PID: %(process)d] | %(levelname)s | %(filename)s:%(lineno)d | %(message)s"
logger = logging.getLogger(__name__)

Listeners: list[type[TopicListener]] = [ImageListener, ModelListenerRpi]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mocked Device")
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="MQTT broker host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=1883,
        help="MQTT broker port (default: 1883)",
    )
    return parser.parse_args()


def create_device(config: MqttConfig) -> MockDevice:
    conn = Retry(lambda: create_connection(config)).get()
    assert conn
    return MockDeviceRPI(conn, listeners=Listeners)


def main() -> None:
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
    args = parse_args()
    device = create_device(MqttConfig(host=args.host, port=args.port))
    device.do_handshake()


if __name__ == "__main__":
    main()
