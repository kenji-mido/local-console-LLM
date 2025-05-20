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
from local_console.core.commands.ota_deploy import get_network_id
from local_console.core.commands.ota_deploy import get_package_version_pkg
from local_console.core.commands.ota_deploy import get_package_version_rpk
from local_console.core.commands.ota_deploy import reverse_bytes_4

PACKAGE_VERSION = b"0311031234560100"
REVERSED_PACKAGE_VERSION = b"1130213065430010"


def test_reverse_bytes_4():
    assert reverse_bytes_4(b"1234") == b"4321"
    assert reverse_bytes_4(b"12345678") == b"43218765"
    assert reverse_bytes_4(b"12345678ABCDEFGH") == b"43218765DCBAHGFE"


def test_get_package_version_pkg(tmp_path):
    pkg_file = tmp_path / "model.pkg"
    pkg_file.write_bytes(b"X" * 16 * 3 + PACKAGE_VERSION)
    assert get_package_version_pkg(pkg_file) == PACKAGE_VERSION


def test_get_package_version_rpk(tmp_path):
    rpk_file = tmp_path / "model.rpk"
    rpk_file.write_bytes(b"X" * 16 * 3 + REVERSED_PACKAGE_VERSION)
    assert get_package_version_rpk(rpk_file) == PACKAGE_VERSION


def test_get_network_id_pkg(tmp_path):
    pkg_file = tmp_path / "model.pkg"
    pkg_file.write_bytes(b"X" * 16 * 3 + PACKAGE_VERSION)
    assert get_network_id(pkg_file) == "123456"


def test_get_network_id_rpk(tmp_path):
    rpk_file = tmp_path / "model.rpk"
    rpk_file.write_bytes(b"X" * 16 * 3 + REVERSED_PACKAGE_VERSION)
    assert get_network_id(rpk_file) == "123456"
