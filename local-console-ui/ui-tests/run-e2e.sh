#!/bin/bash
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

# Runs E2E tests. Assumes Python environment with Local Console and mocked device installed.

local-console -v serve &
PID1=$!

python ../mocked-device/mocked_device/main.py &
PID2=$!

yarn test:e2e
EXIT_CODE=$?

kill $PID1 $PID2

exit $EXIT_CODE
