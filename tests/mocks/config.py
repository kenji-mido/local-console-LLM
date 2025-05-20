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
from local_console.core.config import Config
from local_console.core.schemas.schemas import GlobalConfiguration

from tests.strategies.samplers.configs import GlobalConfigurationSampler


def set_configuration(
    configuration: GlobalConfiguration = GlobalConfigurationSampler(
        num_of_devices=1
    ).sample(),
) -> None:
    # Configure initial state
    config_obj = Config()
    config_obj.data = configuration
    config_obj.save_config()

    # Reset counters
    config_obj._persistency_obj.read_count = 0
    config_obj._persistency_obj.write_count = 0
