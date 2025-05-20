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

from mocked_device.listeners.app import AppListener
from mocked_device.listeners.device_configuration_v2 import (
    DeviceConfigurationV2Listener,
)
from mocked_device.listeners.firmware import FirmwareListener
from mocked_device.listeners.image import ImageListener
from mocked_device.listeners.model import ModelListener
from mocked_device.listeners.reboot import RebootListener
from mocked_device.listeners.streaming_v1 import StreamingV1Listener
from mocked_device.listeners.streaming_v2 import StreamingV2Listener
from mocked_device.mock_v1.device_v1 import MockDeviceV1
from mocked_device.mock_v2.device_v2 import MockDeviceV2
from mocked_device.mqtt.connection import create_connection
from mocked_device.mqtt.event import TopicListener
from mocked_device.mqtt.values import MqttConfig
from mocked_device.retry.retrier import Retry

LOG_FORMAT = "%(asctime)s [%(threadName)s][PID: %(process)d] | %(levelname)s | %(filename)s:%(lineno)d | %(message)s"
logger = logging.getLogger(__name__)

Listeners = [
    FirmwareListener,
    ModelListener,
    AppListener,
    ImageListener,
    RebootListener,
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mocked Device")
    parser.add_argument(
        "--port", type=int, default=1883, help="MQTT broker port (default: 1883)"
    )
    parser.add_argument(
        "--version",
        type=int,
        choices=[1, 2],
        default=1,
        help="Version of the Cloud IF and EVP to be mocked",
    )
    return parser.parse_args()


def create_device(config: MqttConfig, version: int) -> MockDeviceV1 | MockDeviceV2:
    conn = Retry(lambda: create_connection(config)).get()
    assert conn
    logger.info(f"Mocking version {version}")

    listeners: list[type[TopicListener]] = Listeners
    match version:
        case 1:
            listeners.append(StreamingV1Listener)
            return MockDeviceV1(conn, listeners=listeners)

        case 2:
            listeners.append(DeviceConfigurationV2Listener)
            listeners.append(StreamingV2Listener)
            return MockDeviceV2(conn, listeners=listeners)

        case _:
            raise NotImplementedError(f"Device version {version}")


def main() -> None:
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
    args = parse_args()
    device = create_device(MqttConfig(port=args.port), version=args.version)
    device.do_handshake()


if __name__ == "__main__":
    main()
