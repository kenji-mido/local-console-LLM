#!/bin/sh
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

CURR_PATH=$(cd $(dirname $0) && pwd -P)
cd "$CURR_PATH/.."

PRETTIER="./node_modules/.bin/prettier"

if ! [ -x "$PRETTIER" ]; then
  echo "Error: Prettier is not installed. Run 'yarn install' inside local-console-ui."
  exit 1
fi

if [ "$#" -eq 0 ]; then
  echo "Error: This script must be executed from pre-commit."
  exit 1
fi

# Space added to ensure local-console-ui is at the beginning of the path
FILES=$(echo " $@" | sed 's| local-console-ui/| |g')

echo "Running Prettier on the following files: $FILES"
echo "$FILES" | xargs "$PRETTIER" --write
