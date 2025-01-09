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
import io
from base64 import b64encode

from PIL import Image


def fake_image() -> bytes:
    image = Image.new("RGB", (640, 460), (255, 0, 0))

    img_bytes = io.BytesIO()
    image.save(img_bytes, format="JPEG")

    return img_bytes.getvalue()


def fake_image_base64() -> str:
    return b64encode(fake_image()).decode("utf-8")
