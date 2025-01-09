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
import pytest

from oss.utils import get_license_token
from oss.utils import read_licenses_file_list
from oss.utils import simplify_version
from oss.utils import WHITELIST_PATH


@pytest.mark.parametrize(
    "version_1, version_2",
    [
        ("v1", "v1.0.0"),
        ("3.0.0", "v3"),
        ("4.2.0", "4.2"),
    ],
)
def test_simplify_version_are_same(version_1: str, version_2: str):
    assert simplify_version(version_1) == simplify_version(version_2)


@pytest.mark.parametrize(
    "version_1, version_2",
    [
        ("version1", "v1"),
        ("4.2.1", "4.2"),
    ],
)
def test_simplify_version_are_different(version_1: str, version_2: str):
    assert simplify_version(version_1) != simplify_version(version_2)


@pytest.mark.parametrize(
    "license_key_1, license_key_2",
    [
        ("mit", "MIT MIT License"),
        ("BSD 3-Clause", "BSD 2.0"),
        ("BSD 3-Clause", "BSD Revised License"),
        ("Apache-2.0 license", "Apache 2"),
        ("BSD-2-Clause", "FreeBSD"),
        ("BlueOak-1.0.0", "blueoak 1"),
        ("MIT License Version 2.0.0", "mit 2"),
        ("Python Software Foundation License Version 2", "Python v2"),
        ("MIT or Apache 2.0", "MIT / Apache License 2"),
        (
            "Eclipse Public License 2.0 Eclipse Distribution License 1.0",
            "Eclipse Public License 2.0 -OR- Eclipse Distribution License 1.0",
        ),
    ],
)
def test_get_license_keys_are_same(license_key_1: str, license_key_2: str):
    assert get_license_token(license_key_1) == get_license_token(license_key_2)


@pytest.mark.parametrize(
    "license_key_1, license_key_2",
    [
        ("MIT", "MIT 1.0"),
        ("a gpl", "AGPL"),
        ("MIT version1", "MIT v1"),
        ("BSD 2-Clause", "BSD 2.0"),
        ("BSD 3-Clause", "BSD 3.0"),
    ],
)
def test_get_license_keys_are_different(license_key_1: str, license_key_2: str):
    assert get_license_token(license_key_1) != get_license_token(license_key_2)


@pytest.mark.parametrize(
    "license_key",
    [
        ("MIT"),
        ("Eclipse Public License 2.0 Eclipse Distribution License 1.0"),
        ("BSD 2-Clause"),
        ("BSD 3-Clause"),
        ("FreeBSD"),
        ("Python Software Foundation License Version 2"),
        ("BlueOak Version 1.0.0"),
        ("GNU General Public"),
        ("Apache 2.0"),
        ("CC-BY-4"),
        ("BSD 3-Clause New or Revised License"),
    ],
)
def test_good_licenses(license_key: str):
    set_valid_licenses: set[str] = set(read_licenses_file_list(WHITELIST_PATH))
    assert all([key in set_valid_licenses for key in get_license_token(license_key)])


@pytest.mark.parametrize(
    "license_key",
    [
        ("agpl"),
        ("agpl v3"),
        ("sspl"),
        ("GPL"),
        ("GNU Lesser General Public"),
        ("Common Development and Distribution License"),
        ("CDDL"),
        ("ZLib License"),
        ("Apache 1.0"),
        ("CC-BY-NC"),
        ("CC-NC"),
    ],
)
def test_wrong_licenses(license_key: str):
    set_valid_licenses: set[str] = set(read_licenses_file_list(WHITELIST_PATH))
    assert get_license_token(license_key)[0] not in set_valid_licenses
