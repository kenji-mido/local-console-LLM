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
from collections.abc import Generator
from contextlib import contextmanager
from io import BytesIO
from unittest.mock import MagicMock
from unittest.mock import patch


class MockQRCode(MagicMock):
    def __init__(self, fake_image: bytes = b"fake_image_data", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.qr_mocked: MagicMock = MagicMock()
        self.qr_image: MagicMock = MagicMock()
        self.fake_image_data = fake_image
        self.return_value = self.qr_mocked
        self.qr_mocked.make_image.return_value = self.qr_image
        self.qr_image.save.side_effect = self._save_side_effect

    def _save_side_effect(self, fp, format=None):
        if isinstance(fp, BytesIO):
            fp.write(self.fake_image_data)


@contextmanager
def mock_qr() -> Generator[MockQRCode, None, None]:
    with patch("qrcode.main.QRCode", new_callable=MockQRCode) as qr_constructor:
        yield qr_constructor
