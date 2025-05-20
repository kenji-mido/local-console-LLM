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
import json
import logging
from abc import ABC
from abc import abstractmethod
from typing import Any

from local_console.core.enums import config_paths
from local_console.core.enums import DEFAULT_PERSIST_SETTINGS
from local_console.core.error.base import UserException
from local_console.core.error.code import ErrorCodes
from local_console.core.files.exceptions import FileNotFound
from local_console.core.schemas.schemas import DeploymentManifest
from local_console.core.schemas.schemas import DeviceConnection
from local_console.core.schemas.schemas import DeviceID
from local_console.core.schemas.schemas import DeviceListItem
from local_console.core.schemas.schemas import GlobalConfiguration
from local_console.core.schemas.schemas import LocalConsoleConfig
from local_console.core.schemas.schemas import MQTTParams
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.core.schemas.schemas import Persist
from local_console.core.schemas.schemas import WebserverParams
from local_console.utils.singleton import Singleton
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """
    Used for conveying error messages in a framework-agnostic way
    """


class ConfigPersistency(ABC):
    """
    Abstract class for implementations of configuration persistency,
    which should provide a method to read from & write to persistent
    storage.
    """

    @abstractmethod
    def read_config(self) -> GlobalConfiguration: ...

    @abstractmethod
    def save_config(self, conf: GlobalConfiguration) -> None: ...


class OnDisk(ConfigPersistency):

    def read_config(self) -> GlobalConfiguration:
        try:
            with config_paths.config_path.open() as f:
                return GlobalConfiguration(**json.load(f))
        except OSError as e:
            logger.warning("Config file not found")
            raise e
        except Exception as e:
            raise ConfigError(f"Config file not well formed: {e}")

    def save_config(self, conf: GlobalConfiguration) -> None:
        logger.info("Storing configuration")
        config_path = config_paths.config_path
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w") as f:
                f.write(conf.model_dump_json(indent=2))
        except Exception as e:
            raise ConfigError(
                f"Error while generating folder {config_path.parent} or storing configuration: {e}"
            )


class Config(metaclass=Singleton):

    persistency_class: type[ConfigPersistency] = OnDisk

    def __init__(self, initial: GlobalConfiguration | None = None) -> None:
        self._config: GlobalConfiguration = (
            initial if initial else Config.get_default_config()
        )
        self._persistency_obj = Config.persistency_class()

    @property
    def data(self) -> GlobalConfiguration:
        return self._config

    @data.setter
    def data(self, new_data: GlobalConfiguration) -> None:
        self._config = new_data

    @staticmethod
    def get_default_config() -> GlobalConfiguration:
        return GlobalConfiguration(
            devices=[Config._create_device_config("Default", DeviceID(1883))],
            config=LocalConsoleConfig(
                webserver=WebserverParams(host="0.0.0.0", port=0)
            ),
        )

    def read_config(self) -> None:
        self._config = self._persistency_obj.read_config()

    def save_config(self) -> None:
        self._persistency_obj.save_config(self._config)

    def get_config(self) -> GlobalConfiguration:
        return self._config

    def get_device_config(self, key: DeviceID) -> DeviceConnection:
        for device_config in self._config.devices:
            if device_config.id == key:
                return device_config
        raise FileNotFound(
            filename=str(key), message=f"Device for port {key} not found"
        )

    def get_device_config_by_name(self, name: str) -> DeviceConnection:
        for device_config in self._config.devices:
            if device_config.name == name:
                return device_config
        raise FileNotFound(
            filename=str(name), message=f"Device named '{name}' not found"
        )

    def get_persistent_attr(self, key: DeviceID, attr: str) -> Any:
        assert (
            attr in Persist.model_fields.keys()
        ), f"Attribute '{attr}' is not a persistent one."

        for device_config in self._config.devices:
            if device_config.id == key:
                return getattr(device_config.persist, attr)
        raise FileNotFound(
            filename=str(key), message=f"Device for port {key} not found"
        )

    def update_persistent_attr(self, key: DeviceID, attr: str, value: Any) -> None:
        assert (
            attr in Persist.model_fields.keys()
        ), f"Attribute '{attr}' is not a persistent one."

        for device_config in self._config.devices:
            if device_config.id == key:
                setattr(device_config.persist, attr, value)
                self.save_config()
                return
        raise FileNotFound(
            filename=str(key), message=f"Device for port {key} not found"
        )

    def get_first_device_config(self) -> DeviceConnection:
        return self._config.devices[0]

    def rename_entry(self, key: DeviceID, new_name: str) -> None:
        # First, validate by building an associated device record (port number is irrelevant)
        self._create_device_config(new_name, key)

        # If not exceptions raised, then do rename.
        entry: DeviceConnection = next(d for d in self._config.devices if d.id == key)
        entry.name = new_name
        self.save_config()

    def get_deployment(self) -> DeploymentManifest:
        try:
            with open(config_paths.deployment_json) as f:
                deployment_data = json.load(f)
        except Exception:
            raise ConfigError("deployment.json does not exist or is not well formed")
        try:
            return DeploymentManifest(**deployment_data)
        except ValidationError as e:
            missing_field = list(e.errors()[0]["loc"])[1:]
            raise ConfigError(
                f"Missing field in the deployment manifest: {missing_field}"
            )

    def construct_device_record(self, name: str, key: DeviceID) -> DeviceConnection:
        record_lookup = (dev for dev in self.data.devices if dev.id == key)
        conn = next(record_lookup, None)
        if conn is None:
            conn = self._create_device_config(name, key)

        return conn

    def commit_device_record(self, device_conn: DeviceConnection) -> None:
        record_lookup = (dev for dev in self.data.devices if dev.id == device_conn.id)
        if next(record_lookup, None) is None:
            self._config.devices.append(device_conn)

    def remove_device(self, key: DeviceID) -> None:
        if len(self._config.devices) <= 1:
            # Duplicated from device services. Ensures no other ways to modify configuration breaks the invariant.
            raise UserException(
                ErrorCodes.EXTERNAL_ONE_DEVICE_NEEDED,
                "You need at least one device to work with",
            )

        devices_after_remove = [
            connection for connection in self._config.devices if connection.id != key
        ]

        self._config.devices = devices_after_remove

    def get_device_configs(self) -> list[DeviceConnection]:
        return self._config.devices

    def get_device_list_items(self) -> list[DeviceListItem]:
        return [
            DeviceListItem(
                name=device.name,
                port=device.mqtt.port,
                id=device.id,
                onwire_schema=device.onwire_schema,
            )
            for device in self._config.devices
        ]

    @staticmethod
    def _create_device_config(name: str, device_id: DeviceID) -> DeviceConnection:
        try:
            return DeviceConnection(
                mqtt=MQTTParams(
                    host="localhost",
                    port=int(device_id),
                    device_id=None,
                ),
                name=name,
                id=device_id,
                onwire_schema=OnWireProtocol.EVP1,
                persist=DEFAULT_PERSIST_SETTINGS.model_copy(),
            )
        except ValidationError as e:
            raise _render_validation_error(e)

    def reset(self) -> None:
        """
        Allows the reuse of existing `Config` instances (e.g., global variables) without
        needing to create new ones.

        Example:
            config_obj = Config()
        """
        self.data = Config.get_default_config()


def _render_validation_error(error_obj: ValidationError) -> UserException:

    error = error_obj.errors()[0]
    kind = error["type"]
    msg = error["msg"]

    if kind == "string_too_long":
        message = msg.replace("String", "Device name")

        return UserException(
            code=ErrorCodes.EXTERNAL_DEVICE_NAMES_TOO_LONG,
            message=message,
        )
    elif any(kind.startswith(k) for k in ("less_than", "greater_than")):
        message = msg.replace("Input", "MQTT port")

        return UserException(
            ErrorCodes.EXTERNAL_DEVICE_PORTS_MUST_BE_IN_TCP_RANGE,
            message,
        )
    else:
        return UserException(
            ErrorCodes.EXTERNAL_DEVICE_CREATION_VALIDATION,
            msg,
        )
