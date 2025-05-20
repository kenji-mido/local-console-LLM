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

from fastapi.testclient import TestClient
from local_console.core.camera.qr.schema import QRInfo

from tests.mocks.mock_qr import mock_qr


def test_success_get_qr_with_defaults(fa_client: TestClient):
    with (mock_qr() as qr_constructor,):
        response = fa_client.get("/provisioning/qrcode")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"
        qr_constructor.qr_mocked.add_data.assert_called_once_with(
            f"AAIAAAAAAAAAAAAAAAAAAA==N=11;E={QRInfo().mqtt_host};H=1883;t=1;T=pool.ntp.org;U1FS"
        )


def test_get_qr_call_qr_class(fa_client: TestClient):
    with (mock_qr() as qr_constructor,):
        response = fa_client.get(
            "/provisioning/qrcode?mqtt_host=sample.host&mqtt_port=1234&ntp=sample.ntp&ip_address=192.168.1.1&subnet_mask=255.255.255.4&gateway=192.168.1.2&dns=1.1.1.1&wifi_ssid=test&wifi_pass=password"
        )

        qr_constructor.assert_called()
        qr_constructor.qr_mocked.add_data.assert_called_once_with(
            "AAIAAAAAAAAAAAAAAAAAAA==N=11;E=sample.host;H=1234;t=1;S=test;P=password;I=192.168.1.1;K=255.255.255.4;G=192.168.1.2;D=1.1.1.1;T=sample.ntp;U1FS"
        )
        response_data = response.json()
        assert response_data["result"] == "SUCCESS"
        assert response_data["contents"] == base64.b64encode(b"fake_image_data").decode(
            "utf-8"
        )
        assert "expiration_date" in response_data


def test_get_qr_device_not_found(fa_client: TestClient):
    with mock_qr() as qr_constructor:
        response = fa_client.get(
            "/provisioning/qrcode?mqtt_host=sample.host&mqtt_port=1234&ntp=sample.ntp"
        )

        qr_constructor.assert_called()
        qr_constructor.qr_mocked.add_data.assert_called_once_with(
            "AAIAAAAAAAAAAAAAAAAAAA==N=11;E=sample.host;H=1234;t=1;T=sample.ntp;U1FS"
        )
        response_data = response.json()
        assert response_data["result"] == "SUCCESS"
        assert response_data["contents"] == base64.b64encode(b"fake_image_data").decode(
            "utf-8"
        )
        assert "expiration_date" in response_data
