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
import hashlib
import logging
import uuid
from collections.abc import Awaitable
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Optional

from local_console.core.camera.enums import DeployStage
from local_console.core.enums import ModuleExtension
from local_console.core.schemas.schemas import Deployment
from local_console.core.schemas.schemas import DeploymentManifest
from local_console.core.schemas.schemas import DeviceID
from local_console.servers.webserver import combine_url_components
from local_console.servers.webserver import SyncWebserver
from pydantic import BaseModel

logger = logging.getLogger(__name__)


StageNotifyFn = Callable[[DeployStage, DeploymentManifest | None], Awaitable[None]]


class DeploymentSpec(BaseModel):
    modules: dict[str, Path]
    pre_deployment: Deployment

    @classmethod
    def new_empty(cls) -> "DeploymentSpec":
        empty_raw_deployment = Deployment(
            deploymentId=str(uuid.uuid4()),
            instanceSpecs={},
            modules={},
            publishTopics={},
            subscribeTopics={},
        )
        return DeploymentSpec(modules={}, pre_deployment=empty_raw_deployment)

    def collect_modules_from_pre(self) -> None:
        """
        Populate the `modules` field by reading from
        `pre_deployment.modules.[*].downloadUrl`, assuming that
        those values are not actual URLs, but filesystem paths.
        Such assumption might hold when reading deployment manifests
        written by hand by the user.
        """
        assert not self.modules, f"The `modules` dict is already populated: {self}"

        for name, module in self.pre_deployment.modules.items():
            maybe_file = Path(module.downloadUrl)
            if not maybe_file.is_file():
                raise ValueError(
                    f"`pre_deployment` might already be a rendered manifest: {self.pre_deployment}"
                )

            self.modules[name] = maybe_file

    def render_for_webserver(
        self, webserver: SyncWebserver, device_id: DeviceID
    ) -> DeploymentManifest:
        self.collect_modules_from_pre()
        url_root = webserver.url_root_at(device_id)
        dm = self.populate_urls_and_hashes(url_root)
        make_unique_module_ids(dm)
        return dm

    def populate_urls_and_hashes(
        self,
        url_root: str,
    ) -> DeploymentManifest:
        dm = DeploymentManifest(deployment=self.pre_deployment)

        for module, path in self.modules.items():
            mod_hash = calculate_sha256(path)
            url_path = SyncWebserver.url_path_for(path)
            url = combine_url_components(url_root, url_path)

            dm.deployment.modules[module].hash = mod_hash
            dm.deployment.modules[module].downloadUrl = url

        # DeploymentId based on deployment manifest content
        deployment_manifest_hash = hashlib.sha256(str(dm.model_dump()).encode("utf-8"))
        dm.deployment.deploymentId = deployment_manifest_hash.hexdigest()
        return dm

    def enlist_files_in(self, webserver: SyncWebserver) -> None:
        for module in self.modules.values():
            webserver.enlist_file(module)

    def delist_files_in(self, webserver: SyncWebserver) -> None:
        for module in self.modules.values():
            webserver.delist_file(module)


def verify_report(
    deployment_id: str, deploy_status: dict[str, Any]
) -> tuple[bool, bool, bool]:
    matches = deploy_status.get("deploymentId") == deployment_id
    is_finished = deploy_status.get("reconcileStatus") == "ok"

    error_in_modules = any(
        n["status"] == "error" for n in deploy_status.get("modules", {}).values()
    )
    error_in_modinsts = any(
        n["status"] == "error" for n in deploy_status.get("instances", {}).values()
    )
    is_errored = error_in_modinsts or error_in_modules

    return is_finished, matches, is_errored


def get_module_impl(module_file: Path) -> str:
    module_impl = "wasm"
    if module_file.suffix == ModuleExtension.PY.as_suffix:
        module_impl = "python"

    return module_impl


def single_module_manifest_setup(
    module_name: str,
    module_file: Path,
) -> DeploymentSpec:
    """
    Generate a single module, single instance deployment spec.
    """
    deployment = Deployment.model_validate(
        {
            "deploymentId": "",
            "instanceSpecs": {
                module_name: {"moduleId": module_name, "subscribe": {}, "publish": {}}
            },
            "modules": {
                module_name: {
                    "entryPoint": "main",
                    "moduleImpl": get_module_impl(module_file),
                    "downloadUrl": "",
                    "hash": "",
                }
            },
            "publishTopics": {},
            "subscribeTopics": {},
        }
    )
    deployment.modules[module_name].downloadUrl = str(module_file)
    spec = DeploymentSpec(modules={}, pre_deployment=deployment)

    return spec


def make_unique_module_ids(deploy_man: DeploymentManifest) -> None:
    """
    Makes module identifiers in the deployment manifest unique
    across deployments, by suffixing them with a slice of the
    module's hash.
    """
    modules = deploy_man.deployment.modules
    old_to_new = {name: f"{name}-{m.hash[:5]}" for name, m in modules.items()}

    # Update modules
    for old_id, new_id in old_to_new.items():
        module = modules.pop(old_id)
        modules[new_id] = module

    # Update instanceSpecs
    instances = deploy_man.deployment.instanceSpecs
    for instance in instances.values():
        instance.moduleId = old_to_new[instance.moduleId]


def calculate_sha256(path: Path) -> str:
    sha256_hash = hashlib.sha256()
    sha256_hash.update(path.read_bytes())
    return sha256_hash.hexdigest()


def deploy_status_empty(deploy_status: Optional[dict[str, Any]]) -> bool:
    if not deploy_status:
        return True

    if "reconcileStatus" not in deploy_status:
        return True

    if "deploymentId" not in deploy_status:
        return True

    return False
