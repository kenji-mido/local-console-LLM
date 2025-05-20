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
import logging
from base64 import b64encode
from typing import Protocol

import numpy as np
from mocked_device.mock_v2.device_v2 import DirectGetImageRequest
from PIL import Image

logger = logging.getLogger(__name__)

_has_senscord = False
try:
    from senscord import Core
    from senscord import Stream

    _has_senscord = True
except ImportError:
    logger.warning("Using fake camera")


class CameraBase(Protocol):

    def get_image(self, request: DirectGetImageRequest) -> bytes: ...

    def get_image_b64(self, request: DirectGetImageRequest) -> str:
        return b64encode(self.get_image(request)).decode("utf-8")


def request_to_roi_box(
    request: DirectGetImageRequest,
) -> tuple[int, int, int, int]:
    if (
        request.crop_h_offset is None
        or request.crop_v_offset is None
        or request.crop_h_size is None
        or request.crop_v_size is None
    ):
        raise Exception("A request member is None")
    # crop resolution is 2028x1520, image resolution is 640x480
    h_scale = 640 / 2028
    v_scale = 480 / 1520
    return (
        int(request.crop_h_offset * h_scale),
        int(request.crop_v_offset * v_scale),
        int(request.crop_h_size * h_scale),
        int(request.crop_v_size * v_scale),
    )


class PiCamera(CameraBase):
    def __init__(self) -> None:
        self.core = Core()
        self.core.init()
        self.stream: Stream | None = None
        self._stream_started = False

    def _initialize_stream(self) -> None:
        stream_list = self.core.get_stream_list()
        logger.debug(f"Available streams: {stream_list}")

        # If `run_server.sh` is not running, open_stream raises exception
        self.stream = self.core.open_stream("inference_stream")
        self.stream.start()
        self._stream_started = True
        logger.debug("Inference stream started.")

    def get_image(self, request: DirectGetImageRequest) -> bytes:
        if not self._stream_started:
            self._initialize_stream()

        assert self.stream
        frame = self.stream.get_frame(-1)
        channel = frame.get_channel_list()[-1]
        raw_data = channel.get_raw_data()
        data = raw_data.get_bytes()
        self.stream.release_frame(frame)
        logger.debug("Retrieved raw data from channel.")

        array = np.frombuffer(data, dtype=np.uint8).reshape((480, 640, 3))
        image = Image.fromarray(array, mode="RGB")

        # Apply ROI
        x, y, w, h = request_to_roi_box(request)
        crop_box = (x, y, x + w, y + h)
        image = image.crop(crop_box).resize((640, 480))

        # Encode to JPEG
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="JPEG")
        return img_bytes.getvalue()

    def __del__(self) -> None:
        if self.stream:
            self.stream.stop()


class FakeCamera(CameraBase):

    def get_image(self, request: DirectGetImageRequest) -> bytes:
        _, _, w, h = request_to_roi_box(request)
        image = Image.new("RGB", (w, h), (255, 0, 0))

        img_bytes = io.BytesIO()
        image.save(img_bytes, format="JPEG")
        return img_bytes.getvalue()


def get_camera() -> CameraBase:
    if _has_senscord:
        return PiCamera()
    return FakeCamera()
