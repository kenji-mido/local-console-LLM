/**
 * Copyright 2024 Sony Semiconductor Solutions Corp.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

import { DeviceStatus, LocalDevice } from '@app/core/device/device';
import { expect } from '@playwright/test';
import { DeviceList } from '@samplers/device';
import { NICS } from '@samplers/nics';
import { createDevice } from '../../tools/interactions';
import { defer } from '../../tools/promise';
import { test } from './../fixtures/fixtures';

test.describe(
  'Provisioning Hub',
  {
    annotation: {
      type: 'Provisioning Hub',
      description:
        'This test suit covers the FrontEnd tests involving the Provisioning Hub tab',
    },
  },
  () => {
    test.describe(
      'Happy paths',
      {
        annotation: {
          type: 'Happy paths',
          description:
            'These tests cover cases when the application encounters no errors or hiccups',
        },
      },
      () => {
        test('Preview correctly sends the `preview` parameter when requesting stream to start', async ({
          page,
        }) => {
          const deviceList = DeviceList.sample();
          const firstDevice = <LocalDevice>deviceList.devices[0];
          const previewDeferred = defer<Boolean | undefined>();
          // Given
          await page.route('**/devices?limit=500', async (route) => {
            await route.fulfill({ json: deviceList });
          });
          await page.route('**/devices', async (route) => {
            await route.fulfill({ json: { result: 'SUCCESS' } });
          });
          await page.route(
            `**/devices/${firstDevice.device_id}/command`,
            async (route) => {
              const body = route.request().postDataJSON();
              previewDeferred.resolve(body['extra']['preview']);
              route.fulfill({ json: { result: 'ERROR' }, status: 404 });
            },
          );

          // When
          await page.goto('http://localhost:4200/provisioning-hub');
          await createDevice(
            page,
            firstDevice.device_name,
            Number(firstDevice.device_id),
          );
          await page.getByTestId('option-1').click();
          await page.getByLabel('Start preview').isEnabled();
          await page.getByLabel('Start preview').click();

          // Then
          expect(
            await previewDeferred,
            'On preview, the application needs to properly notify the backend through extra.preview',
          ).toBeTruthy();
        });

        test(
          'Device creation send correct information',
          {
            annotation: {
              type: 'Device creation send correct information',
              description:
                'This test makes sure that, when registering new devices, the correct information is being sent.',
            },
          },
          async ({ page }) => {
            // Given
            let getCallCount = 0;
            const deviceList = DeviceList.sample();
            deviceList.devices.splice(1, 2);
            const emptyList = DeviceList.sampleEmpty();
            const listResponses = [emptyList, deviceList];
            const device_name = 'Mydevicename';
            const mqtt_port = 12345;
            const device = <LocalDevice>deviceList.devices[0];
            device.device_name = device_name;
            device.device_id = mqtt_port.toString();
            let sentName = '';
            let sentPort = 0;

            await page.route('**/devices?limit=500', async (route) => {
              await route.fulfill({ json: deviceList });
            });

            await page.route(
              'http://localhost:8000/devices',
              async (route, request) => {
                if (request.method() === 'POST') {
                  const body = JSON.parse(request.postData() || '{}');
                  sentName = body.device_name;
                  sentPort = body.id;
                  getCallCount++;
                  await route.continue();
                }
              },
            );

            // When
            await page.goto('http://localhost:4200/provisioning-hub');
            await createDevice(page, device_name, mqtt_port);

            // Then
            expect(
              sentName,
              'When calling the endpoint to create a device, the correct Device Name is sent',
            ).toBe(device_name);
            expect(
              sentPort,
              'When calling the endpoint to create a device, the correct MQTT Port is sent',
            ).toBe(mqtt_port);
          },
        );

        test(
          'Device form can be reset',
          {
            annotation: {
              type: 'Device form can be reset',
              description:
                'This test first fills all device registratioin fields, and then makes sure than when clicking Reset they are all emptied.',
            },
          },
          async ({ page }) => {
            // Given
            const device_name = 'My device name';
            const mqtt_port = 12345;
            const deviceList = DeviceList.sample();
            await page.route('**/devices?limit=500', async (route) => {
              await route.fulfill({ json: deviceList });
            });

            // When
            await page.goto('http://localhost:4200/provisioning-hub');
            await page
              .getByTestId('device-register-name')
              .locator('input')
              .fill(device_name);
            await page
              .getByTestId('device-register-port')
              .locator('input')
              .fill(mqtt_port.toString());
            await page.getByTestId('device-reset').click();

            // Then
            expect(
              await page
                .getByTestId('device-register-name')
                .locator('input')
                .textContent(),
              'The Device Name text box should be empty.',
            ).not.toBe(device_name);
            expect(
              await page
                .getByTestId('device-register-port')
                .locator('input')
                .textContent(),
              'The MQTT Port text box should be empty.',
            ).not.toBe(mqtt_port.toString());
            await expect(
              page.getByTestId('device-reset'),
              'The Reset button should be disabled, as all text boxes are empty.',
            ).toBeDisabled();
          },
        );

        test(
          'QR form can be reset',
          {
            annotation: {
              type: 'QR form can be reset',
              description:
                'This test first fills all QR fields, and then makes sure than when clicking Reset they are all emptied.',
            },
          },
          async ({ page }) => {
            const deviceList = DeviceList.sample();
            await page.route('**/devices?limit=500', async (route) => {
              await route.fulfill({ json: deviceList });
            });
            // When
            await page.goto('http://localhost:4200/provisioning-hub');
            await page.getByTestId('option-1').click();
            // Then
            //NTP parameter
            await page.getByTestId('ntp').getByTestId('text-input').fill('ntp');
            //IP address
            await page
              .getByTestId('toggle_static_ip')
              .locator('div')
              .getByRole('img')
              .click();
            await page
              .getByTestId('ip_address')
              .getByTestId('text-input')
              .fill('mock_ip');
            //wifi ssid
            await page
              .getByTestId('toggle_wifi_ssid')
              .locator('div')
              .getByRole('img')
              .click();
            await page
              .getByTestId('wifi_ssid')
              .getByTestId('text-input')
              .fill('wifi-ssid');
            //Reset
            await page.getByRole('button', { name: 'Reset' }).click();

            await expect(
              page.getByTestId('ntp').getByTestId('text-input'),
              'The Network Time Server text box should be empty.',
            ).toBeEmpty();
            await expect(
              page.getByTestId('ip_address').getByTestId('text-input'),
              'The MQTT Broker text box should be empty.',
            ).toBeEmpty();
            await expect(
              page.getByTestId('wifi_ssid').getByTestId('text-input'),
              'The Wi-Fi SSID text box should be empty.',
            ).toBeEmpty();

            await expect(
              page.getByRole('button', { name: 'Reset' }),
              'The Reset button should be disabled, as all text boxes are empty.',
            ).toBeDisabled();
          },
        );
      },
    );

    test.describe(
      'Sad paths',
      {
        annotation: {
          type: 'Sad paths',
          description:
            'These tests cover situations leading to errors due to improper usage of the app, to ensure they are properly handled',
        },
      },
      () => {
        test(
          'Streaming is stopped if device cannot return images in 30s',
          {
            annotation: {
              type: 'Streaming is stopped if device cannot return images in 30s',
              description:
                'This simulates a device is unable to return streaming images, and checks that, when trying to visualize the stream, an error message is raised',
            },
          },
          async ({ page }) => {
            const deviceList = DeviceList.sample();
            const firstDevice = <LocalDevice>deviceList.devices[0];
            // Given
            await page.route('**/devices?limit=500', async (route) => {
              await route.fulfill({ json: deviceList });
            });

            await page.route('**/devices', async (route) => {
              await route.fulfill({ json: { result: 'SUCCESS' } });
            });

            await page.route(
              `**/devices/${firstDevice.device_id}/command`,
              async (route) => {
                route.fulfill({ json: { result: 'ERROR' } });
              },
            );

            // When
            await page.goto('http://localhost:4200/provisioning-hub');
            await createDevice(
              page,
              firstDevice.device_name,
              Number(firstDevice.device_id),
            );
            await page.getByTestId('option-1').click();
            await page.getByLabel('Start preview').isEnabled();
            await page.getByLabel('Start preview').click();

            // Then
            await expect(
              page.getByTestId('drawing'),
              'The streaming should not have started.',
            ).not.toHaveClass(/streaming/, {
              timeout: 30000 + 2000,
            });
            // and alert prompt is visible
            await expect(
              page.getByTestId('alert-dialog-title'),
              "An error message saying 'Preview stopped' should appear.",
            ).toContainText('Preview stopped');
            await expect(
              page.getByTestId('prompt-action-cancel'),
              'A button to close the error message must appear.',
            ).toBeVisible();
          },
        );

        test(
          'Device registration should do nothing if form is not filled in properly',
          {
            annotation: {
              type: 'Device registration should do nothing if form is not filled in properly',
              description:
                'This test makes sure that the button to register a device is not enabled unless all required fields are filled in.',
            },
          },
          async ({ page }) => {
            // Given
            const emptyList = DeviceList.sampleEmpty();
            const device_name = 'My device name';
            const mqtt_port = '12345';

            // When
            await page.goto('http://localhost:4200/provisioning-hub');

            // Then
            await expect(
              page.getByTestId('device-register'),
              'The Register button is not enabled if no information is filled in.',
            ).not.toBeEnabled();
            await page
              .getByTestId('device-register-name')
              .locator('input')
              .fill(device_name);
            await expect(
              page.getByTestId('device-register'),
              'The Register button is not enabled if only the device name is filled in.',
            ).not.toBeEnabled();
            await page
              .getByTestId('device-register-name')
              .locator('input')
              .fill('');
            await page
              .getByTestId('device-register-port')
              .locator('input')
              .fill(mqtt_port.toString());
            await expect(
              page.getByTestId('device-register'),
              'The Register button is not enabled if only the port information is filled in.',
            ).not.toBeEnabled();
          },
        );

        // @ACC_PFREQ-1510.1
        test('Preview button disabled while device is disconnected', async ({
          page,
        }) => {
          const deviceList = DeviceList.sample();
          const start = Date.now();
          deviceList.devices = [deviceList.devices[0]];
          deviceList.devices[0].connection_state = DeviceStatus.Disconnected;

          // Given
          await page.route('**/devices?limit=500', async (route) => {
            await route.fulfill({ json: deviceList });
          });

          // When
          await page.goto('http://localhost:4200/provisioning-hub');
          await page
            .getByTestId('hub-mode-selector')
            .getByTestId('option-1')
            .click();

          // Then
          await expect(page.getByTestId('start-preview')).toBeDisabled();
        });

        // @ACC_PFREQ-1510.3
        test(
          'Preview button is enabled while connected and disabled when device is disconnected',
          {
            annotation: {
              type: 'Preview button is enabled while connected and disabled when device is disconnected',
              description:
                'This test checks that the stream preview button is disabled if the device has been disconnected. Checked in port 1884',
            },
          },
          async ({ page }) => {
            const deviceList = DeviceList.sample();
            const firstDevice = <LocalDevice>deviceList.devices[0];
            firstDevice.connection_state = DeviceStatus.Connected;
            // Emulates device is connected
            await page.route('**/devices?limit=500', async (route) => {
              await route.fulfill({ json: deviceList });
            });

            await page.route('**/devices', async (route) => {
              route.fulfill({ json: { result: 'SUCCESS' } });
            });

            await page.goto('http://localhost:4200/provisioning-hub');

            await page.getByTestId('option-0').click();
            await createDevice(
              page,
              firstDevice.device_name,
              Number(firstDevice.device_id),
            );

            await page.getByTestId('option-1').click();

            const previewLocator = await page.getByTestId('start-preview');

            await expect(
              previewLocator,
              'Device is connected and the start preview button is enabled',
            ).toBeEnabled();

            firstDevice.connection_state = DeviceStatus.Disconnected;
            deviceList.devices[0] = firstDevice;
            // Emulates device is disconnected
            await page.route('**/devices?limit=500', async (route) => {
              await route.fulfill({ json: deviceList });
            });

            await page.waitForRequest('**/devices?limit=500');

            await expect(
              previewLocator,
              'Device is disconnected and the start preview button is disabled',
            ).toBeDisabled();
          },
        );
      },
    );

    test.describe(
      'NICs',
      {
        annotation: {
          type: 'NICs',
          description:
            'These tests cover interactions with the NICs searchable input dropdown',
        },
      },
      () => {
        test('Should show spinner animation while loading NICs', async ({
          page,
        }) => {
          const deviceList = DeviceList.sample();
          // Given
          await page.route('**/devices?limit=500', async (route) => {
            await route.fulfill({ json: deviceList });
          });
          await page.route(`**/interfaces`, async (route) => {
            setTimeout(
              route.fulfill.bind(route, {
                json: { network_interfaces: NICS.sampleList() },
              }),
              1000,
            );
          });

          // When
          await page.goto('http://localhost:4200/provisioning-hub');
          await page
            .getByTestId('hub-mode-selector')
            .getByTestId('option-1')
            .click();

          // Then
          const nicsPanel = page.getByTestId('nics');
          await expect(nicsPanel.getByTestId('loading-spinner')).toBeVisible({
            timeout: 10000,
          });

          // And after loading the NICs
          await expect(
            nicsPanel.getByTestId('loading-spinner'),
          ).not.toBeVisible({
            timeout: 10000,
          });
          await expect(nicsPanel.getByTestId('nics-input')).toBeVisible();
        });

        // @ACC_PFREQ-1480.3
        test('Should load and display all NICs', async ({ page }) => {
          const deviceList = DeviceList.sample();
          // Given
          await page.route('**/devices?limit=500', async (route) => {
            await route.fulfill({ json: deviceList });
          });
          const nics = NICS.sampleList();
          await page.route(`**/interfaces`, async (route) => {
            route.fulfill({ json: { network_interfaces: nics } });
          });

          // When
          await page.goto('http://localhost:4200/provisioning-hub');
          await page
            .getByTestId('hub-mode-selector')
            .getByTestId('option-1')
            .click();

          // Then
          const nicsPanel = page.getByTestId('nics');
          await expect(nicsPanel.getByTestId('nics-input')).toBeVisible();

          // And after entering editing mode
          await nicsPanel.getByTestId('facade').click();

          await expect(nicsPanel.getByTestId('editing-input')).toBeVisible();
          await expect(
            nicsPanel.getByTestId('editing-input').locator('input'),
          ).toBeFocused();
          await expect(nicsPanel.getByTestId('dropdown')).toBeVisible();
          const renderedIPs = await nicsPanel
            .getByTestId('dropdown')
            .locator('.nic-ip')
            .allTextContents();
          const matchingIPs = nics.map((nic) => renderedIPs.includes(nic.ip));

          expect(matchingIPs).toHaveLength(3);
        });

        // @ACC_PFREQ-1509.1
        // @ACC_PFREQ-1480.1
        test('Should select first available NIC by default when only one is retrieved', async ({
          page,
        }) => {
          const deviceList = DeviceList.sample();
          // Given
          await page.route('**/devices?limit=500', async (route) => {
            await route.fulfill({ json: deviceList });
          });
          const nics = NICS.sampleList().slice(0, 1);
          await page.route(`**/interfaces`, async (route) => {
            route.fulfill({ json: { network_interfaces: nics } });
          });

          // When
          await page.goto('http://localhost:4200/provisioning-hub');
          await page
            .getByTestId('hub-mode-selector')
            .getByTestId('option-1')
            .click();

          // Then
          const nicsPanel = page.getByTestId('nics');
          await expect(nicsPanel.getByTestId('nics-input')).toBeVisible();
          const facade = nicsPanel.getByTestId('facade');
          await expect(facade).toContainText(nics[0].name);
          await expect(facade).toContainText(nics[0].ip);
        });

        // @ACC_PFREQ-1509.2
        // @ACC_PFREQ-1480.2
        test('Should not select default if multiple NICs are present', async ({
          page,
        }) => {
          const deviceList = DeviceList.sample();
          // Given
          await page.route('**/devices?limit=500', async (route) => {
            await route.fulfill({ json: deviceList });
          });
          const nics = NICS.sampleList();
          await page.route(`**/interfaces`, async (route) => {
            route.fulfill({ json: { network_interfaces: nics } });
          });

          // When
          await page.goto('http://localhost:4200/provisioning-hub');
          await page
            .getByTestId('hub-mode-selector')
            .getByTestId('option-1')
            .click();

          // Then
          const nicsPanel = page.getByTestId('nics');
          await expect(nicsPanel.getByTestId('nics-input')).toBeVisible();
          const facade = nicsPanel.getByTestId('facade');
          await expect(facade).not.toContainText(nics[0].name);
          await expect(facade).not.toContainText(nics[0].ip);
        });

        // @ACC_PFREQ-1509.2
        // @ACC_PFREQ-1480.2
        test('Should disable QR generation if NIC not selected', async ({
          page,
        }) => {
          const deviceList = DeviceList.sample();
          // Given
          await page.route('**/devices?limit=500', async (route) => {
            await route.fulfill({ json: deviceList });
          });
          const nics = NICS.sampleList();
          await page.route(`**/interfaces`, async (route) => {
            route.fulfill({ json: { network_interfaces: nics } });
          });

          // When
          await page.goto('http://localhost:4200/provisioning-hub');
          await page
            .getByTestId('hub-mode-selector')
            .getByTestId('option-1')
            .click();

          // Then
          const nicsPanel = page.getByTestId('nics');
          await expect(nicsPanel.getByTestId('nics-input')).toBeVisible();
          const facade = nicsPanel.getByTestId('facade');
          await expect(page.getByTestId('qr-generate')).toBeDisabled();

          // And when selecting a NIC
          await nicsPanel.getByTestId('facade').click();
          await nicsPanel
            .getByTestId('dropdown')
            .getByTestId('option-2')
            .click();
          await expect(page.getByTestId('qr-generate')).toBeEnabled();
        });

        // @ACC_PFREQ-1509.3
        test('Should enable Reset when NIC is selected', async ({ page }) => {
          const deviceList = DeviceList.sample();
          // Given
          await page.route('**/devices?limit=500', async (route) => {
            await route.fulfill({ json: deviceList });
          });
          const nics = NICS.sampleList();
          await page.route(`**/interfaces`, async (route) => {
            route.fulfill({ json: { network_interfaces: nics } });
          });

          // When
          await page.goto('http://localhost:4200/provisioning-hub');
          await page
            .getByTestId('hub-mode-selector')
            .getByTestId('option-1')
            .click();

          // Then
          const nicsPanel = page.getByTestId('nics');
          await expect(nicsPanel.getByTestId('nics-input')).toBeVisible();
          const facade = nicsPanel.getByTestId('facade');
          await expect(page.getByTestId('qr-reset')).toBeDisabled();

          // And when selecting a NIC
          await nicsPanel.getByTestId('facade').click();
          await nicsPanel
            .getByTestId('dropdown')
            .getByTestId('option-2')
            .click();
          await expect(page.getByTestId('qr-reset')).toBeEnabled();
        });

        test('Should reset NIC selection if multiple NICs', async ({
          page,
        }) => {
          const deviceList = DeviceList.sample();
          // Given
          await page.route('**/devices?limit=500', async (route) => {
            await route.fulfill({ json: deviceList });
          });
          const nics = NICS.sampleList();
          await page.route(`**/interfaces`, async (route) => {
            route.fulfill({ json: { network_interfaces: nics } });
          });

          // When
          await page.goto('http://localhost:4200/provisioning-hub');
          await page
            .getByTestId('hub-mode-selector')
            .getByTestId('option-1')
            .click();
          const nicsPanel = page.getByTestId('nics');
          await nicsPanel.getByTestId('facade').click();
          await nicsPanel
            .getByTestId('dropdown')
            .getByTestId('option-2')
            .click();

          // Then
          const facade = nicsPanel.getByTestId('facade');
          await expect(facade).toContainText(nics[2].name);
          await expect(facade).toContainText(nics[2].ip);

          // And when reset is clicked
          await page.getByTestId('qr-reset').click();

          // Then
          await expect(facade).not.toContainText(nics[2].name);
          await expect(facade).not.toContainText(nics[2].ip);
          await expect(page.getByTestId('qr-reset')).toBeDisabled();
          await expect(page.getByTestId('qr-generate')).toBeDisabled();
        });

        test('Should not set searchable input as dirty if only one NIC', async ({
          page,
        }) => {
          const deviceList = DeviceList.sample();
          // Given
          await page.route('**/devices?limit=500', async (route) => {
            await route.fulfill({ json: deviceList });
          });
          const nics = NICS.sampleList().slice(0, 1);
          await page.route(`**/interfaces`, async (route) => {
            route.fulfill({ json: { network_interfaces: nics } });
          });

          // When
          await page.goto('http://localhost:4200/provisioning-hub');
          await page
            .getByTestId('hub-mode-selector')
            .getByTestId('option-1')
            .click();

          // Then
          const nicsPanel = page.getByTestId('nics');
          const facade = nicsPanel.getByTestId('facade');
          await expect(facade).toContainText(nics[0].name);
          await expect(facade).toContainText(nics[0].ip);
          await expect(page.getByTestId('qr-reset')).toBeDisabled();
        });

        test('Should reset NIC to default first if only one present', async ({
          page,
        }) => {
          const deviceList = DeviceList.sample();
          // Given
          await page.route('**/devices?limit=500', async (route) => {
            await route.fulfill({ json: deviceList });
          });
          const nics = NICS.sampleList().slice(0, 1);
          await page.route(`**/interfaces`, async (route) => {
            route.fulfill({ json: { network_interfaces: nics } });
          });

          // When
          await page.goto('http://localhost:4200/provisioning-hub');
          await page
            .getByTestId('hub-mode-selector')
            .getByTestId('option-1')
            .click();
          const nicsPanel = page.getByTestId('nics');
          await page
            .getByTestId('ntp')
            .getByTestId('text-input')
            .fill('192.168.3.4');

          // Then
          await expect(page.getByTestId('qr-reset')).toBeEnabled();

          // And when reset is clicked
          await page.getByTestId('qr-reset').click();

          // Then value is still set (default)
          const facade = nicsPanel.getByTestId('facade');
          await expect(facade).toContainText(nics[0].name);
          await expect(facade).toContainText(nics[0].ip);
        });

        test('Should not enable Generate QR button while searching NIC', async ({
          page,
        }) => {
          const deviceList = DeviceList.sample();
          // Given
          await page.route('**/devices?limit=500', async (route) => {
            await route.fulfill({ json: deviceList });
          });
          const nics = NICS.sampleList();
          await page.route(`**/interfaces`, async (route) => {
            route.fulfill({ json: { network_interfaces: nics } });
          });

          // When
          await page.goto('http://localhost:4200/provisioning-hub');
          await page
            .getByTestId('hub-mode-selector')
            .getByTestId('option-1')
            .click();
          const nicsPanel = page.getByTestId('nics');
          await nicsPanel.getByTestId('facade').click();
          await nicsPanel
            .getByTestId('editing-input')
            .locator('input')
            .fill('abcd');

          // Then
          await expect(page.getByTestId('qr-generate')).toBeDisabled();
          await expect(page.getByTestId('qr-reset')).toBeDisabled();
        });

        // @ACC_PFREQ-1480.4
        test('Should filter NICs based on search terms', async ({ page }) => {
          const deviceList = DeviceList.sample();
          // Given
          await page.route('**/devices?limit=500', async (route) => {
            await route.fulfill({ json: deviceList });
          });
          const nics = NICS.sampleList();
          nics[0].ip = '192.168.1.38';
          nics[1].ip = '10.34.2.2';
          nics[2].ip = '172.18.1.1';
          await page.route(`**/interfaces`, async (route) => {
            route.fulfill({ json: { network_interfaces: nics } });
          });

          // When searching for '192.168'
          await page.goto('http://localhost:4200/provisioning-hub');
          await page
            .getByTestId('hub-mode-selector')
            .getByTestId('option-1')
            .click();
          const nicsPanel = page.getByTestId('nics');
          await nicsPanel.getByTestId('facade').click();
          await nicsPanel
            .getByTestId('editing-input')
            .locator('input')
            .fill('192.168');

          // Then only one NIC appears
          let renderedIPs = await nicsPanel
            .getByTestId('dropdown')
            .locator('.nic-ip')
            .allTextContents();
          expect(renderedIPs.length).toBe(1);

          // And when searching for '1.'
          await nicsPanel
            .getByTestId('editing-input')
            .locator('input')
            .fill('1.');

          // Then two appear
          renderedIPs = await nicsPanel
            .getByTestId('dropdown')
            .locator('.nic-ip')
            .allTextContents();
          expect(renderedIPs.length).toBe(2);
        });

        // @ACC_PFREQ-1509.3
        test('Should send selected NIC IP value for QR generation', async ({
          page,
        }) => {
          const deviceList = DeviceList.sample();
          // Given
          await page.route('**/devices?limit=500', async (route) => {
            await route.fulfill({ json: deviceList });
          });
          const nics = NICS.sampleList();
          await page.route(`**/interfaces`, async (route) => {
            route.fulfill({ json: { network_interfaces: nics } });
          });
          const deferred = { resolve: (ip: string) => {} };
          const receivedIp = new Promise(
            (resolve) => (deferred.resolve = <any>resolve),
          );

          await page.route('**/provisioning/qrcode*', async (route) => {
            const url = new URL(route.request().url());
            const mqttHost = url.searchParams.get('mqtt_host');
            const ip = mqttHost;
            deferred.resolve(ip || '');
            await route.continue();
          });

          // When
          await page.goto('http://localhost:4200/provisioning-hub');
          await page
            .getByTestId('hub-mode-selector')
            .getByTestId('option-1')
            .click();
          const nicsPanel = page.getByTestId('nics');
          await nicsPanel.getByTestId('facade').click();
          await nicsPanel
            .getByTestId('dropdown')
            .getByTestId('option-2')
            .click();
          await page.getByTestId('qr-generate').click();

          // Then
          await expect(receivedIp).resolves.toBe(nics[2].ip);
        });

        test('Should disable Preview if device is Connecting', async ({
          page,
        }) => {
          const deviceList = DeviceList.sample();
          const onlyOneDevice = deviceList.devices[0];
          onlyOneDevice.connection_state = DeviceStatus.Connecting;
          deviceList.devices = [onlyOneDevice];
          // Given
          await page.route('**/devices?limit=500', async (route) => {
            await route.fulfill({ json: deviceList });
          });

          // When
          await page.goto('http://localhost:4200/provisioning-hub');
          await page
            .getByTestId('hub-mode-selector')
            .getByTestId('option-1')
            .click();

          // Then
          const previewLocator = page.getByTestId('start-preview');

          await expect(
            previewLocator,
            'Device is Connecting and the start preview button is disabled',
          ).toBeDisabled();
        });
      },
    );
  },
);
