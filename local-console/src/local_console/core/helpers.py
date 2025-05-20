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
import base64
import json
import logging
import re
from collections.abc import Iterator
from typing import Any
from typing import Callable
from typing import TypeVar

import trio
from local_console.clients.agent import Agent
from local_console.core.camera.enums import MQTTTopics
from local_console.core.schemas.schemas import DeploymentManifest
from local_console.core.schemas.schemas import DesiredDeviceConfig
from local_console.core.schemas.schemas import OnWireProtocol
from pydantic import BaseModel
from pydantic import ValidationError
from pydantic_core import SchemaValidator

logger = logging.getLogger(__name__)


def is_valid(model: BaseModel) -> bool:
    """
    Validate a pydantic model against the model's schema.
    """
    schema_validator = SchemaValidator(schema=model.__pydantic_core_schema__)
    try:
        schema_validator.validate_python(model.__dict__)
        return True
    except ValidationError:
        return False


TI = TypeVar("TI")


def safe_get_next(iterator: Iterator[TI], default: TI) -> TI:
    """
    Safely extract the next value of an iterator (e.g. a generator comprehension).
    """
    try:
        return next(iterator)
    except (StopIteration, AttributeError):
        return default


def is_default_or_none(value: Any) -> bool:
    """
    Returns True if 'value' is None or, for certain known types
    (list, tuple), it's a 'default' (empty).
    """
    match value:
        case None:
            return True
        case []:
            return True
        case ():
            return True
        case True | False:
            return False
        case int() | float() | str():
            return False
        case _:
            return False


TM = TypeVar("TM", bound=BaseModel)


def merge_model_instances(target: TM, source: TM) -> None:
    """
    Recursively update fields in 'target' **in place** with values from 'source',
    **only** if the corresponding field in 'target' is None or a 'default' value,
    and 'source' has a non-default in that field.
    """
    # We iterate over the *declared* fields of the target model
    for field_name in target.model_fields:
        target_val = getattr(target, field_name)
        source_val = getattr(source, field_name)

        # If both target and source fields are themselves Pydantic models, recurse:
        if isinstance(target_val, BaseModel) and isinstance(source_val, BaseModel):
            merge_model_instances(target_val, source_val)
        else:
            # None values are values that are not included in the report
            if source_val is not None:
                setattr(target, field_name, source_val)


async def device_configure(
    mqtt: Agent,
    onwire_schema: OnWireProtocol,
    desired_device_config: DesiredDeviceConfig,
) -> None:
    """
    :param config: Configuration of the module instance.
    """
    message: dict = {
        "desiredDeviceConfig": {
            "desiredDeviceConfig": {
                "configuration/$agent/report-status-interval-max": desired_device_config.reportStatusIntervalMax,
                "configuration/$agent/report-status-interval-min": desired_device_config.reportStatusIntervalMin,
                "configuration/$agent/configuration-id": "",
                "configuration/$agent/registry-auth": {},
            }
        }
    }
    payload = json.dumps(message)
    await mqtt.publish(MQTTTopics.ATTRIBUTES.value, payload=payload)


async def initialize_handshake(mqtt: Agent, timeout: int = 5) -> None:
    async with mqtt.mqtt_scope(
        [
            MQTTTopics.ATTRIBUTES_REQ.value,
        ]
    ):
        assert mqtt.nursery
        assert mqtt.client

        with trio.move_on_after(timeout):
            async with mqtt.client.messages() as mgen:
                async for msg in mgen:
                    await check_attributes_request(
                        mqtt, msg.topic, msg.payload.decode()
                    )
        logger.debug("Exiting initialized handshake")


async def check_attributes_request(
    agent: Agent, topic: str, payload: dict[str, Any]
) -> bool:
    """
    Checks that a given MQTT message (as provided by its topic and payload)
    conveys a request from the device's agent for data attributes set in the
    MQTT broker.
    """
    got_request = False
    result = re.search(r"^v1/devices/me/attributes/request/(\d+)$", topic)
    if result:
        got_request = True
        req_id = result.group(1)
        logger.debug(
            "Got attribute request (id=%s) with payload: '%s'",
            req_id,
            payload,
        )
        await agent.publish(
            f"v1/devices/me/attributes/response/{req_id}",
            "{}",
        )
    return got_request


async def publish_configure(
    mqtt: Agent,
    onwire_schema: OnWireProtocol,
    instance_id: str,
    topic: str,
    config: str,
) -> None:
    # EVP2 does not enforce base64 encoding
    if onwire_schema == OnWireProtocol.EVP1:
        config = base64.b64encode(config.encode("utf-8")).decode("utf-8")

    message: dict = {f"configuration/{instance_id}/{topic}": config}
    payload = json.dumps(message)
    logger.debug(f"payload: {payload}")
    await mqtt.publish(MQTTTopics.ATTRIBUTES.value, payload=payload)


async def publish_deploy(
    mqtt: Agent, onwire_schema: OnWireProtocol, to_deploy: DeploymentManifest
) -> None:
    if onwire_schema == OnWireProtocol.EVP2:
        deployment = to_deploy.render_for_evp2()
    elif onwire_schema == OnWireProtocol.EVP1:
        deployment = to_deploy.render_for_evp1()

    await mqtt.publish(MQTTTopics.ATTRIBUTES.value, payload=deployment)


def read_only_loop(mqtt: Agent, subs_topics: list[str], message_task: Callable) -> None:

    async def _loop_client(
        mqtt: Agent, subs_topics: list[str], message_task: Callable
    ) -> None:
        try:
            async with mqtt.mqtt_scope(subs_topics):
                assert mqtt.nursery is not None
                cs = mqtt.nursery.cancel_scope
                mqtt.nursery.start_soon(message_task, cs, mqtt)
                await trio.sleep_forever()
        except* KeyboardInterrupt:
            pass

    trio.run(_loop_client, mqtt, subs_topics, message_task)
