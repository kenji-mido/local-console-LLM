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
import time

from mocked_device.device import create_device
from mocked_device.mock.deployment.app.behavior import deploy_app_behavior
from mocked_device.mock.deployment.firmware.behavior import deploy_firmware_behavior
from mocked_device.mock.handshake.behavior import handshake_behavior
from mocked_device.mock.rpc.image.behavior import deploy_image_behavior
from mocked_device.mock.rpc.streaming.behavior import streaming_behavior
from mocked_device.mqtt.values import MqttConfig

LOG_FORMAT = "%(asctime)s [%(threadName)s][PID: %(process)d] | %(levelname)s | %(filename)s:%(lineno)d | %(message)s"
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mocked Device")
    parser.add_argument(
        "--port", type=int, default=1883, help="MQTT broker port (default: 1883)"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    device = create_device(MqttConfig(port=args.port))
    logger.info("Connected to device")
    handshake_behavior().apply_behavior(device)
    logger.info("Handshake made")
    deploy_firmware_behavior().apply_behavior(device)
    deploy_image_behavior().apply_behavior(device)
    streaming_behavior().apply_behavior(device)
    deploy_app_behavior().apply_behavior(device)
    time.sleep(6000)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
    main()
