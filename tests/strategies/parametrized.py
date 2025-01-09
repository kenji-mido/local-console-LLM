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

VALID_IPS = [
    "192.168.1.1",  # Simple IPv4
    "10.0.0.2",  # Private IPv4
    "127.0.0.1",  # Localost IPv4
]

INVALID_IPS = [
    "256.256.256.256",  # Invalid IPv4 (octets out of range)
    "192.168.1.1/33",  # Invalid IPv4 subnet (CIDR out of range)
    "2001:db8:::1",  # Invalid IPv6 (consecutive colons used incorrectly)
    "192.168.1.abc",  # Invalid IPv4 (contains non-numeric characters)
    "abcd::12345",  # Invalid IPv6 (one group too long)
    "::1/129",  # Invalid IPv6 subnet (CIDR out of range)
    "<",  # Invalid text
    " ",  # Invalid with space
    "not.val.id.ip",  # Invalid text with dots
]
