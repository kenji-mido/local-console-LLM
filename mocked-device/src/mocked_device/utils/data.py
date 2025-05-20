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
from typing import Any
from typing import TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)


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
            # Otherwise, we have a "leaf" field. Check if we should overwrite:
            # if is_default_or_none(target_val) and not is_default_or_none(source_val):
            if target_val != source_val and not is_default_or_none(source_val):
                setattr(target, field_name, source_val)
