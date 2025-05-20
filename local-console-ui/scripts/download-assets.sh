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

CURR_PATH=$(cd $(dirname $0) && pwd -P)
cd "$CURR_PATH/../.."

TYPE=${1:-ES}
VERSION=${2:-v2}

if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
  echo "Usage: $0 [TYPE] [VERSION]"
  echo
  echo "Downloads sample test assets for Local Console UI tests."
  echo
  echo "Arguments:"
  echo "  TYPE     MP or ES (default: ES)"
  echo "  VERSION  v1 or v2 (default: v2)"
  echo
  echo "Example:"
  echo "  $0 MP v1      # Download assets for MP device with version v1"
  echo "  $0            # Uses defaults: ES v2"
  exit 0
fi

PLATFORM=$(uname -m)
if [[ "$PLATFORM" == "arm64" || "$PLATFORM" == "aarch64" ]]; then
  DOCKER_PLATFORM="linux/arm64"
else
  DOCKER_PLATFORM="linux/amd64"
fi

if [ "$TYPE" = "ES" ] && [ "$VERSION" = "v2" ]; then
  echo "Downloading sample assets for ES v2..."
  docker run --platform "$DOCKER_PLATFORM" ghcr.io/midokura/local-console/local-console-test-assets:ES-v2-v0.0.1 \
    tar -c /files | \
    tar -x --strip-components=1 -C local-console-ui/ui-tests/tools/samples/
else
  echo "No assets to download for type '$TYPE' and version '$VERSION'"
fi
