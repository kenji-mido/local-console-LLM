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
import logging
import os
import subprocess as sp
from pathlib import Path
from shutil import copy
from shutil import copytree

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s"
logging.basicConfig(format=LOG_FORMAT, level=logging.DEBUG)
logger = logging.getLogger(__name__)


def main() -> None:
    root = Path(__file__).parents[2]
    assert root.joinpath(".github").is_dir()

    drive = Path(f'{os.environ["SystemDrive"]}\\')
    assets_target_root = drive / "s"

    # Electron UI assets
    ui_source = root / "local-console-ui"
    sp.run("yarn install", shell=True, check=True, cwd=ui_source)
    ui_assets_source = ui_source / "dist" / "win-unpacked"
    ui_assets_target = assets_target_root / "ui"
    lc_exe = ui_assets_target / "LocalConsole.exe"
    if not lc_exe.is_file():
        logger.info("Building Electron assets")
        sp.run("yarn package:electron --win", shell=True, check=True, cwd=ui_source)
    copy_assets(ui_assets_source, ui_assets_target)

    # Windows installer build assets
    winbuild_assets_source = root / "local-console" / "windows"
    copy_assets(winbuild_assets_source, assets_target_root / "windows")
    new_spec = patch_innosetup_spec(
        root / "inno-setup.iss", assets_target_root, ui_assets_target
    )

    # Version file
    ver_file = root / "VERSION"
    version = ver_file.read_text().strip()
    copy(ver_file, assets_target_root)

    # Wheel file
    # Replace symlink from repo with hard copy
    ver_file_in_py_source = root / "local-console" / "VERSION"
    ver_file_in_py_source.unlink(missing_ok=True)
    copy(ver_file, ver_file_in_py_source)
    # Run wheel build if necessary
    wheel_file_source = root / f"local_console-{version}-py3-none-any.whl"
    if not wheel_file_source.is_file():
        logger.info("Building python wheel")
        sp.run(
            r"python -m build --wheel --outdir . .\local-console", shell=True, cwd=root
        )
    copy(wheel_file_source, assets_target_root)

    # Installer build
    installer_exe = assets_target_root / "Output" / f"local-console-setup-{version}.exe"
    if not installer_exe.is_file():
        logger.info("Building installer for Windows")
        iscc = drive / "Program Files (x86)" / "Inno Setup 6" / "ISCC.exe"
        assert iscc.is_file()
        sp.run(
            [str(iscc), "/Qp", "/O+", str(new_spec)], check=True, cwd=assets_target_root
        )


def copy_assets(source: Path, target: Path) -> None:
    if target.is_dir():
        print(f"Target dir {target} already exists. Won't copy from {source}")
        return

    copytree(source, target)


def move_assets(source: Path, target: Path) -> None:
    if target.is_dir():
        print(f"Target dir {target} already exists. Won't move from {source}")
        return

    source.rename(target)


def patch_innosetup_spec(spec_file: Path, target_root: Path, ui_sub: Path) -> Path:
    spec = spec_file.read_text()
    patched = spec.replace("local-console\\", "").replace(
        "local-console-ui\\dist\\win-unpacked", ui_sub.name
    )

    patched_spec_file = target_root / spec_file.name
    patched_spec_file.write_text(patched)

    return patched_spec_file


if __name__ == "__main__":
    main()
