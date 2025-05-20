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

# Requires multiplatform builder,
# $ docker buildx create --use --platform=linux/arm64,linux/amd64 --name multi-platform-builder
# $ docker buildx inspect --bootstrap

# Specify files 1 per line
readarray -t FILES <<EOF
classification-es.pkg
detection-es.pkg
edge_app_classification.1.1.2.signed.aot
edge_app_detection.1.1.2.signed.aot
EOF

# Specify docker image tag
IMAGE_TAG="ghcr.io/midokura/local-console/local-console-test-assets:ES-v2-v0.0.1"

echo "This script builds and pushes the image to $IMAGE_TAG."
read -p "Are you sure you want to continue? [y/N]: " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 1
fi

CURR_PATH=$(cd "$(dirname "$0")" && pwd -P)
cd "$CURR_PATH/../ui-tests/tools/samples"

# Create a temporary build directory
BUILD_DIR=$(mktemp -d)
mkdir -p "$BUILD_DIR/files"

# Copy files into the build context
cp "${FILES[@]}" "$BUILD_DIR/files/"

# Create Dockerfile
cat > "$BUILD_DIR/Dockerfile" <<EOF
FROM alpine
COPY files /files
CMD ["echo", "Files are inside the container!"]
EOF

# Build the Docker image
docker buildx build --platform linux/amd64,linux/arm64 -t "$IMAGE_TAG" --push "$BUILD_DIR"

# Clean up
rm -rf "$BUILD_DIR"
