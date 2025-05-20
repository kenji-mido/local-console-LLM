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

import { waitFor } from '@app/core/common/time.utils';
import { DeploymentStatusOut } from '@app/core/deployment/deployment';
import { DeviceStatus, LocalDevice } from '@app/core/device/device';
import { isSysModule } from '@app/core/module/module';
import { test as base, expect, type Page } from '@playwright/test';
import { loadFileIntoFileInput } from '../tools/interactions';
import { logservice } from '../tools/logservice';
import { LocalConsoleServer } from './backend';
import { DeviceManager, DeviceType, MockedDevice, RealDevice } from './devices';
import { screenshotOnError } from './screenshot';

const isWindows = process.platform === 'win32';

/**
 * The following is implementing the "Page Object Model",
 * as explained at https://playwright.dev/docs/pom.
 */
export class TestBase {
  public readonly page: Page;
  readonly testOutputDir: string;
  readonly server: LocalConsoleServer;
  public devices: { [port: number]: DeviceManager };
  readonly ECIfVersion: number;

  constructor(
    readonly _page: Page,
    testOutputDir: string,
    host: string,
  ) {
    this.page = _page;
    this.testOutputDir = testOutputDir;
    this.ECIfVersion = parseInt(process.env['ECI_VERSION']!);
    this.server = new LocalConsoleServer(this.testOutputDir, host);
    this.devices = {};
  }

  public async requiresDevice(
    port: number,
    deviceType: string,
    configPath: string,
  ): Promise<void> {
    if (!this.devices.hasOwnProperty(port)) {
      logservice.debug(`Expecting device at port ${port}. Will create it.`);
      this.devices[port] =
        deviceType === DeviceType.REAL
          ? new RealDevice(
              port,
              this.testOutputDir,
              this.ECIfVersion,
              configPath,
            )
          : new MockedDevice(
              port,
              this.testOutputDir,
              this.ECIfVersion,
              configPath,
            );
    }
  }

  public async waitForDeviceReady(port: number) {
    const connectionTimeout = 300000;
    const statusTimeout = 300000;

    let device = this.devices[port];
    await device.start();

    logservice.log('Connecting device...');
    let connectionState = DeviceStatus.Disconnected;
    let startTime = Date.now();
    while (connectionState !== DeviceStatus.Connected) {
      const info = await device.getDeviceInfo();
      connectionState = info.connection_state;
      if (Date.now() - startTime > connectionTimeout) {
        this.server.stop();
        throw new Error('Device has not connected before timeout');
      }
      await waitFor(100);
    }
    logservice.log('Device is connected!');

    /**
     * Ensures that the device is fully ready and connected before performing the operation.
     *
     * Even if the device appears to be connected, it might still be in a state where it's not fully ready
     * to execute commands, such as after a forced reboot or while it's in the process of connecting.
     */
    try {
      await device.runLCCommand('deploy', '-e');
      logservice.log('Undeploy success.');
    } catch {
      logservice.error('Retrying undeploy...');
    }

    //Refresh for timeout
    let isStatusValid = false;
    startTime = Date.now();
    while (!isStatusValid) {
      isStatusValid = await device.isStatusCorrect();
      if (Date.now() - startTime > statusTimeout) {
        this.server.stop();
        throw new Error('Status has not arrived before timeout');
      }
      await waitFor(30000);
    }
    logservice.log('Status has arrived!');
  }

  public async checkSensorFw(port: number, targetFw: string): Promise<void> {
    let isFwSensorReady = false;
    let startTime = Date.now();
    const fwTimeout = 200000;

    let device = this.devices[port];
    while (!isFwSensorReady) {
      const response: LocalDevice = await device.getDeviceInfo();
      const sysModule = response.modules?.find(isSysModule);
      isFwSensorReady =
        sysModule?.property.configuration?.device_info?.sensors?.at(0)
          ?.firmware_version !== targetFw;
      if (Date.now() - startTime > fwTimeout) {
        throw new Error('Device is not reporting the sensor fw change');
      }
    }
  }

  public async resetFirmware(fwType: string, device: DeviceManager) {
    if (device instanceof MockedDevice) {
      logservice.log('Skipping reset for mocked device ');
      return;
    }

    await this.page.getByRole('button', { name: 'Reset' }).click();
    await this.page.locator('app-toggle').getByRole('img').click();

    let fileInputLoc;
    let fwFile;
    if (fwType === 'sensor') {
      await this.checkSensorFw(device.port, '020300');
      fileInputLoc = this.page.getByTestId('sensor-fw-selector');
      fwFile = device.sampleFiles['prevSensorFw'];
      await this.page.getByRole('textbox', { name: '010707' }).fill('020300');
    } else if (fwType === 'main') {
      fileInputLoc = this.page.getByTestId('chip-fw-selector');
      fwFile = device.sampleFiles['prevMainFw'];
      await this.page.getByRole('textbox', { name: 'D700F6' }).fill('0700E2');
    }

    await loadFileIntoFileInput(this.page, `samples/${fwFile}`, fileInputLoc!);

    //deploy
    await this.page.getByRole('button', { name: 'Deploy' }).click();
    //confirm deploy
    await this.page
      .locator('.cdk-dialog-container')
      .getByRole('button', { name: 'Deploy' })
      .click();

    await expect(this.page.locator('tbody')).toContainText(`${fwFile}`);

    await expect(
      this.page.locator('tbody'),
      'Make sure the deployment has finished',
    ).not.toContainText(DeploymentStatusOut.Running, { timeout: 0 });

    const status = await this.page.locator('tbody').innerText();
    expect(status, 'Make sure there are no failing deployments').not.toContain(
      DeploymentStatusOut.Error,
    ); // matching is case and space sensitive

    expect(status, 'Make sure deployments are successful').toContain(
      DeploymentStatusOut.Success,
    ); // matching is case and space sensitive
  }
}

type FixturesType = {
  fixture: TestBase;
  screenshotOnError: void;
};

/**
 * The following is to be used by test cases, as explained at
 * https://playwright.dev/docs/test-fixtures
 */
export const test = base.extend<FixturesType>({
  fixture: async ({ page }, use, testInfo) => {
    logservice.log(`Starting test: ${testInfo.title}`);

    const defaultPort = 1883;
    const fixture = new TestBase(
      page,
      testInfo.outputDir,
      process.env['IP_ADDRESS']!,
    );

    // Generate configuration file before starting server
    await fixture.server.generateConfigJSON(defaultPort, fixture.ECIfVersion);
    await fixture.server.start();

    await fixture.requiresDevice(
      defaultPort,
      process.env['DEVICE_TYPE']!,
      fixture.server.getConfigPath(),
    );

    logservice.info('Starting test.');
    await use(fixture);
    logservice.info('Ending test.');

    if (testInfo.status === testInfo.expectedStatus)
      logservice.log('Test passed. Cleaning up...');
    else
      logservice.error(
        `Test failed. Cleaning up... Errors=${JSON.stringify(testInfo.errors)}`,
      );

    // Clean device up. If mocked, just kill it.
    await fixture.devices[defaultPort].stop();

    logservice.log('Stopping backend...');

    await fixture.server.stop();
  },
  screenshotOnError: [screenshotOnError, { auto: true }],
});
