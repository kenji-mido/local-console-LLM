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

import psutil
from local_console.fastapi.routes.interfaces.dto import NetworkInterface
from local_console.fastapi.routes.interfaces.dto import NetworkInterfaceList
from local_console.fastapi.routes.interfaces.dto import NetworkStatus
from local_console.utils.local_network import get_network_ifaces


class InterfacesController:

    def _to_interfaces_dto(
        self, name: str, status: bool, addr_info: str
    ) -> NetworkInterface:
        return NetworkInterface(
            name=name,
            ip=addr_info,
            status=NetworkStatus.UP if status else NetworkStatus.DOWN,
        )

    def get_interfaces(self) -> NetworkInterfaceList:
        ifaces_dict = dict(get_network_ifaces())  # type:ignore
        infos = psutil.net_if_addrs()
        # dict with {iface: ip} , ip value is [empty] if NIC is not IPv4
        addrs_infos = {}
        for iface in ifaces_dict.keys():
            if iface not in infos:
                continue
            for info in infos[iface]:
                if info.family == socket.AddressFamily.AF_INET:
                    addrs_infos[iface] = info.address
                    break

        return NetworkInterfaceList(
            network_interfaces=[
                self._to_interfaces_dto(iface, ifaces_dict[iface], ip)
                for iface, ip in addrs_infos.items()
            ]
        )
