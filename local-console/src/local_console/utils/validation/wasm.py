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
"""
WASM File validation leveraging the WebAssembly Binary Toolkit:
https://github.com/WebAssembly/wabt
"""
import logging
import os
import subprocess
import sys
from pathlib import Path
from shutil import which
from tempfile import TemporaryDirectory

logger = logging.getLogger(__name__)


class WABTError(Exception):
    """
    Represents errors during attempted usages of the WABT suite.
    """


def get_wasm_validate() -> str:
    """
    For linux, this has no relevant effects.
    For windows, the installer script placed the flatc binary
                 within the virtualenv's scripts directory.
    """
    env_root = str(Path(sys.executable).parent)
    current_path = os.environ.get("PATH", "")
    if env_root not in current_path.split(os.pathsep):
        os.environ["PATH"] = current_path + os.pathsep + env_root

    # Resolve the path to the binary from the PATH
    wasm_validate_path = which("wasm-validate")
    if not wasm_validate_path:
        raise WABTError("wasm-validate not found in PATH")
    else:
        return wasm_validate_path


def is_valid_wasm_binary(file_name: Path, module: bytes) -> bool:

    valid = False
    try:
        with TemporaryDirectory() as tempdir:
            test_file = Path(tempdir) / file_name.name
            test_file.write_bytes(module)

            binary_path = get_wasm_validate()
            # Enable all to prevent:
            # 000063f: error: memory may not be shared: threads not allowed
            subprocess.run(
                [binary_path, str(test_file), "--enable-all"],
                check=True,
            )
            valid = True
    except Exception as e:
        logger.warning(f"WASM module validation error: {e}")

    return valid
