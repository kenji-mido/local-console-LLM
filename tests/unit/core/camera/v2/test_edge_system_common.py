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
import json

from local_console.core.camera.v2.edge_system_common import EdgeSystemCommon
from local_console.core.camera.v2.edge_system_common import update_mqtt_endpoint
from local_console.core.camera.v2.edge_system_common import update_not_none_fields
from local_console.core.config import Config


def test_initial_system_info() -> None:
    # Check first report by device
    config = EdgeSystemCommon(
        **{
            "systemInfo": {
                "os": "NuttX",
                "arch": "xtensa",
                "evp_agent": "v1.40.0",
                "evp_agent_commit_hash": "19ba152d5ad174999ac3a0e669eece54b312e5d1",
                "wasmMicroRuntime": "v2.1.0",
                "protocolVersion": "EVP2-TB",
            },
            "state/$agent/report-status-interval-min": 3,
            "state/$agent/report-status-interval-max": 180,
            "deploymentStatus": {"instances": {}, "modules": {}},
        }
    )
    assert config.system_info.os == "NuttX"
    assert config.system_info.arch == "xtensa"
    assert config.report_status_interval_max == 180
    assert config.report_status_interval_min == 3
    assert config.deployment_status != {}


def test_initial_reporting() -> None:
    # Device has 2 reports at boot:
    # Initial report without `PRIVATE_endpoint_settings` and `periodic_setting`
    # Second with those values
    current = EdgeSystemCommon(
        **{
            "state/$system/device_info": '{"device_manifest":"","chips":[{"name":"main_chip","id":"","hardware_version":"","temperature":0,"loader_version":"010300","loader_hash":"","update_date_loader":"","firmware_version":"0.6.5","firmware_hash":"","update_date_firmware":"","ai_models":[]},{"name":"sensor_chip","id":"100A50500A2012062364012000000000","hardware_version":"1","temperature":34,"loader_version":"020301","loader_hash":"","update_date_loader":"1970-01-01T00:00:06.000Z","firmware_version":"820204","firmware_hash":"","update_date_firmware":"1970-01-01T00:00:06.000Z","ai_models":[{"version":"","hash":"","update_date":""},{"version":"","hash":"","update_date":""},{"version":"","hash":"","update_date":""},{"version":"","hash":"","update_date":""}]}]}',
            "state/$system/device_states": '{"power_states":{"source":[{"type":0,"level":100}],"in_use":0,"is_battery_low":false},"process_state":"Idle","hours_meter":12,"bootup_reason":0,"last_bootup_time":"2025-03-03T17:19:36.597Z"}',
            "state/$system/wireless_setting": '{"req_info":{"req_id":""},"sta_mode_setting":{"ssid":"","password":"","encryption":0},"res_info":{"res_id":"","code":0,"detail_msg":"ok"}}',
            "state/$system/system_settings": '{"req_info":{"req_id":""},"led_enabled":true,"temperature_update_interval":10,"log_settings":[{"filter":"main","level":3,"destination":0,"storage_name":"","path":""},{"filter":"sensor","level":3,"destination":0,"storage_name":"","path":""},{"filter":"companion_fw","level":3,"destination":0,"storage_name":"","path":""},{"filter":"companion_app","level":3,"destination":0,"storage_name":"","path":""}],"res_info":{"res_id":"","code":0,"detail_msg":"ok"}}',
            "state/$system/device_capabilities": '{"is_battery_supported":false,"supported_wireless_mode":3,"is_periodic_supported":false,"is_sensor_postprocess_supported":true}',
            "state/$system/network_settings": '{"req_info":{"req_id":""},"ip_method":0,"ntp_url":"pool.ntp.org","static_settings_ipv6":{"ip_address":"","subnet_mask":"","gateway_address":"","dns_address":""},"static_settings_ipv4":{"ip_address":"","subnet_mask":"","gateway_address":"","dns_address":""},"proxy_settings":{"proxy_url":"","proxy_port":0,"proxy_user_name":"","proxy_password":""},"res_info":{"res_id":"","code":0,"detail_msg":"ok"}}',
            "state/$system/PRIVATE_reserved": '{"schema":"dtmi:com:sony_semicon:aitrios:sss:edge:system:t3p;2"}',
        }
    )
    assert current.device_info.chips[0].id == ""
    assert current.device_info.chips[1].id == "100A50500A2012062364012000000000"
    assert not current.private_endpoint_setting

    # Parse second report
    new = EdgeSystemCommon(
        **{
            "state/$system/device_info": '{"device_manifest":"","chips":[{"name":"main_chip","id":"","hardware_version":"","temperature":0,"loader_version":"010300","loader_hash":"","update_date_loader":"","firmware_version":"0.6.5","firmware_hash":"","update_date_firmware":"","ai_models":[]},{"name":"sensor_chip","id":"100A50500A2012062364012000000000","hardware_version":"1","temperature":34,"loader_version":"020301","loader_hash":"","update_date_loader":"1970-01-01T00:00:06.000Z","firmware_version":"820204","firmware_hash":"","update_date_firmware":"1970-01-01T00:00:06.000Z","ai_models":[{"version":"","hash":"","update_date":""},{"version":"","hash":"","update_date":""},{"version":"","hash":"","update_date":""},{"version":"","hash":"","update_date":""}]}]}',
            "state/$system/device_states": '{"power_states":{"source":[{"type":0,"level":100}],"in_use":0,"is_battery_low":false},"process_state":"Idle","hours_meter":12,"bootup_reason":0,"last_bootup_time":"2025-03-03T17:19:36.597Z"}',
            "state/$system/wireless_setting": '{"req_info":{"req_id":""},"sta_mode_setting":{"ssid":"","password":"","encryption":0},"res_info":{"res_id":"","code":0,"detail_msg":"ok"}}',
            "state/$system/system_settings": '{"req_info":{"req_id":""},"led_enabled":true,"temperature_update_interval":10,"log_settings":[{"filter":"main","level":3,"destination":0,"storage_name":"","path":""},{"filter":"sensor","level":3,"destination":0,"storage_name":"","path":""},{"filter":"companion_fw","level":3,"destination":0,"storage_name":"","path":""},{"filter":"companion_app","level":3,"destination":0,"storage_name":"","path":""}],"res_info":{"res_id":"","code":0,"detail_msg":"ok"}}',
            "state/$system/device_capabilities": '{"is_battery_supported":false,"supported_wireless_mode":3,"is_periodic_supported":false,"is_sensor_postprocess_supported":true}',
            "state/$system/network_settings": '{"req_info":{"req_id":""},"ip_method":0,"ntp_url":"pool.ntp.org","static_settings_ipv6":{"ip_address":"","subnet_mask":"","gateway_address":"","dns_address":""},"static_settings_ipv4":{"ip_address":"","subnet_mask":"","gateway_address":"","dns_address":""},"proxy_settings":{"proxy_url":"","proxy_port":0,"proxy_user_name":"","proxy_password":""},"res_info":{"res_id":"","code":0,"detail_msg":"ok"}}',
            "state/$system/PRIVATE_reserved": '{"schema":"dtmi:com:sony_semicon:aitrios:sss:edge:system:t3p;2"}',
            "state/$system/PRIVATE_endpoint_settings": '{"req_info":{"req_id":""},"endpoint_url":"192.168.1.22","endpoint_port":1883,"protocol_version":"TB","res_info":{"res_id":"","code":0,"detail_msg":"ok"}}',
            "state/$system/periodic_setting": '{"req_info":{"req_id":""},"operation_mode":0,"recovery_method":0,"interval_settings":[{"base_time":"00.00","capture_interval":120,"config_interval":240},{"base_time":"00.00","capture_interval":120,"config_interval":240}],"ip_addr_setting":"dhcp","res_info":{"res_id":"","code":0,"detail_msg":"ok"}}',
        }
    )

    # Update and verify `current` is updated
    update_not_none_fields(current, new)
    assert current.private_endpoint_setting
    assert current.private_endpoint_setting == new.private_endpoint_setting


def test_endpoint_update() -> None:
    config = Config().get_config()
    assert config.devices[0].mqtt.host == "localhost"
    # Parse second report
    new = EdgeSystemCommon(
        **{
            "state/$system/PRIVATE_endpoint_settings": '{"req_info":{"req_id":""},"endpoint_url":"192.168.1.22","endpoint_port":1883,"protocol_version":"TB","res_info":{"res_id":"","code":0,"detail_msg":"ok"}}',
        }
    )

    # Update and verify `current` is updated
    update_mqtt_endpoint(new)
    assert config.devices[0].mqtt.host == "192.168.1.22"


def test_endpoint_update_no_reserved() -> None:
    config = Config().get_config()
    assert config.devices[0].mqtt.host == "localhost"
    # Parse second report
    new = EdgeSystemCommon(**{})

    # Update and verify `current` is updated
    update_mqtt_endpoint(new)
    assert config.devices[0].mqtt.host == "localhost"


def test_endpoint_update_no_port_match() -> None:
    config = Config().get_config()
    assert config.devices[0].mqtt.host == "localhost"
    # Parse second report
    new = EdgeSystemCommon(
        **{
            "state/$system/PRIVATE_endpoint_settings": '{"req_info":{"req_id":""},"endpoint_url":"192.168.1.22","endpoint_port":1885,"protocol_version":"TB","res_info":{"res_id":"","code":0,"detail_msg":"ok"}}',
        }
    )

    # Update and verify `current` is updated
    update_mqtt_endpoint(new)
    assert config.devices[0].mqtt.host == "localhost"


def test_edge_app_state() -> None:
    payload = {"req_info": {"req_id": ""}}
    new = EdgeSystemCommon(
        **{
            "state/node/edge_app": json.dumps(payload),
        }
    )
    assert "node" in new.edge_app
    assert "another_module_id" not in new.edge_app

    assert new.edge_app["node"] == payload


def test_multiple_edge_app_state() -> None:
    payload1 = {"req_info": {"req_id": "1234"}}
    payload2 = {"req_info": {"req_id": "5678"}}
    new = EdgeSystemCommon(
        **{
            "state/node/edge_app": json.dumps(payload1),
            "state/another_module_id/edge_app": json.dumps(payload2),
        }
    )
    assert "node" in new.edge_app
    assert "another_module_id" in new.edge_app

    assert new.edge_app["node"] == payload1
    assert new.edge_app["another_module_id"] == payload2
