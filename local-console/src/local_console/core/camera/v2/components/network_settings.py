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
from pydantic import BaseModel


class ProxySettings(BaseModel):
    proxy_url: str = ""
    proxy_port: int = -1
    proxy_user_name: str = ""
    proxy_password: str = ""


class StaticAddrSettings(BaseModel):
    ip_address: str
    subnet_mask: str
    gateway_address: str
    dns_address: str


class NetworkSettings(BaseModel):
    req_info: dict
    ip_method: int
    ntp_url: str
    static_settings_ipv6: StaticAddrSettings
    static_settings_ipv4: StaticAddrSettings
    proxy_settings: ProxySettings
    res_info: dict
