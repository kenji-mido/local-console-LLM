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
import socket
from unittest.mock import MagicMock
from unittest.mock import patch

from fastapi import status
from fastapi.testclient import TestClient
from local_console.fastapi.routes.health import controller
from local_console.fastapi.routes.interfaces.controller import (
    InterfacesController,
)
from local_console.fastapi.routes.interfaces.dependencies import (
    interfaces_controller,
)
from local_console.fastapi.routes.interfaces.dto import NetworkInterface
from local_console.fastapi.routes.interfaces.dto import NetworkInterfaceList
from local_console.fastapi.routes.interfaces.dto import NetworkStatus
from psutil._common import snicaddr

from tests.strategies.samplers.files import NetworkInterfaceSampler


def test_get_interfaces_endpoint(fa_client: TestClient):
    controller = MagicMock()
    fa_client.app.dependency_overrides[interfaces_controller] = lambda: controller

    element = NetworkInterfaceSampler().sample()
    controller.get_interfaces.return_value = NetworkInterfaceList(
        network_interfaces=[element]
    )

    result = fa_client.get("/interfaces")

    assert result.status_code == status.HTTP_200_OK
    assert result.json()["network_interfaces"][0] == element.model_dump(mode="json")


def test_get_interfaces_controller():
    controller = InterfacesController()
    with (
        patch(
            "local_console.fastapi.routes.interfaces.controller.get_network_ifaces"
        ) as mock_get_network_ifaces,
        patch(
            "local_console.fastapi.routes.interfaces.controller.psutil.net_if_addrs"
        ) as mock_net_if_addrs,
    ):
        name_1 = "eth0"
        name_2 = "wl123"
        status_1 = True
        status_2 = False
        address_1 = "192.168.1.10"
        address_2 = "192.168.0.1"

        mock_get_network_ifaces.return_value = [(name_1, status_1), (name_2, status_2)]
        mock_net_if_addrs.return_value = {
            name_1: [
                snicaddr(
                    socket.AddressFamily.AF_INET,
                    address_1,
                    "255.255.255.0",
                    "192.168.1.255",
                    None,
                )
            ],
            name_2: [
                snicaddr(
                    socket.AddressFamily.AF_INET,
                    address_2,
                    "255.255.255.0",
                    "192.168.1.255",
                    None,
                )
            ],
        }

        detected_interfaces = controller.get_interfaces()
        assert len(detected_interfaces.network_interfaces) == 2
        assert detected_interfaces.network_interfaces[0] == NetworkInterface(
            name=name_1, ip=address_1, status=NetworkStatus.UP
        )
        assert detected_interfaces.network_interfaces[1] == NetworkInterface(
            name=name_2, ip=address_2, status=NetworkStatus.DOWN
        )


def test_get_interfaces_controller_net_not_compatible_ip():
    controller = InterfacesController()
    with (
        patch(
            "local_console.fastapi.routes.interfaces.controller.get_network_ifaces"
        ) as mock_get_network_ifaces,
        patch(
            "local_console.fastapi.routes.interfaces.controller.psutil.net_if_addrs"
        ) as mock_net_if_addrs,
    ):
        name_1 = "eth0"
        status_1 = True
        address_1 = "192.168.1.10"

        mock_get_network_ifaces.return_value = [(name_1, status_1)]
        mock_net_if_addrs.return_value = {
            name_1: [
                snicaddr(
                    socket.AddressFamily.AF_INET6,
                    address_1,
                    "255.255.255.0",
                    "192.168.1.255",
                    None,
                )
            ],
        }

        detected_interfaces = controller.get_interfaces()
        assert len(detected_interfaces.network_interfaces) == 0
        assert detected_interfaces == NetworkInterfaceList(network_interfaces=[])
