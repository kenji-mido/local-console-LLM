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

import { randomString } from '@app/core/common/random.utils';
import { LocalDevice } from '@app/core/device/device';
import { isSysModule } from '@app/core/module/module';
import { join, resolve } from 'path';
import { logservice } from '../tools/logservice';
import { BackgroundProcess } from '../tools/proc-manager';
import {
  fetchRetry,
  formatAsCommand,
  pythonPath,
  runLCCommand,
} from './lc-shell';

const mockedSampleFiles: { [key: string]: string } = {
  mainFw: 'firmware.bin',
  sensorFw: 'firmware.fpk',
  classificationApp: 'classification.xtensa.signed.aot',
  detectionApp: 'detection.xtensa.signed.aot',
  classificationModel: 'model.pkg',
  detectionModel: 'model.pkg',
};

const realSampleFiles: { [key: string]: string } = {
  // If you want to run the tests locally you get the files by running
  // the following,
  // `./local-console-ui/scripts/download-assets.sh`
  prevMainFw: '0700E2.bin',
  mainFw: '0700FEPD.bin',
  prevSensorFw: '020300.fpk',
  sensorFw: '010707.fpk',
  detectionApp: 'edge_app_detection.1.1.2.signed.aot',
  detectionModel: 'detection-es.pkg',
  classificationApp: 'edge_app_classification.1.1.2.signed.aot',
  classificationModel: 'classification-es.pkg',
};

export enum DeviceType {
  MOCKED = 'mocked',
  REAL = 'real',
}

/**
 * This interface is what device type implementations must provide.
 */
export interface DeviceManager {
  port: number;
  logFile: string;
  ECIfVersion: number;
  configPath: string;
  sampleFiles: { [key: string]: string };

  start(): Promise<void>;
  stop(): Promise<void>;

  runLCCommand(lc_command: string, lc_command_args: string): Promise<void>;
  getDeviceInfo(): Promise<LocalDevice>;
  isStatusCorrect(): Promise<boolean>;
}

export class RealDevice implements DeviceManager {
  port: number;
  logFile: string;
  ECIfVersion: number;
  configPath: string;
  sampleFiles: { [key: string]: string } = realSampleFiles;

  constructor(
    port: number,
    logsDir: string,
    ECIfVersion: number,
    configPath: string,
  ) {
    this.port = port;
    this.logFile = '';
    this.ECIfVersion = ECIfVersion;
    this.configPath = configPath;
  }

  async runLCCommand(
    lc_command: string,
    lc_command_args: string,
  ): Promise<void> {
    const idPrelude = `--port ${this.port}`;
    await runLCCommand(
      `--config-dir ${this.configPath} ${lc_command} ${idPrelude} ${lc_command_args}`,
    );
  }

  async start(): Promise<void> {
    // reboot is done at stop
  }

  async stop(): Promise<void> {
    // Reset command
    let command: string;

    if (this.ECIfVersion == 1) {
      command = `backdoor-EA_Main Reboot {}`;
    } else if (this.ECIfVersion == 2) {
      command = `\\$system reboot {}`;
    }
    await this.runLCCommand(`rpc`, command!);
  }

  async getDeviceInfo(): Promise<LocalDevice> {
    const response = await fetchRetry(
      //TODO modularize the WebAPI port here
      `http://localhost:8000/devices/${this.port}`,
      2000,
      3,
    );
    return response.json() as Promise<LocalDevice>;
  }

  async isStatusCorrect(): Promise<boolean> {
    const info = await this.getDeviceInfo();
    const sysModule = info.modules?.find(isSysModule);

    const deviceInfo = sysModule?.property.configuration?.device_info;
    const ai_models = deviceInfo?.ai_models ?? [];
    const isAiModelsReady = ai_models.length === 0;

    logservice.log(`device info: ${JSON.stringify(deviceInfo)}`);

    if (!isAiModelsReady) {
      const cmdSpec = {
        targets: [],
        req_info: {
          req_id: `id-for-undeploy-ai-${randomString()}`,
        },
      };
      const jsonStr = formatAsCommand(cmdSpec);
      logservice.log(jsonStr);

      await this.runLCCommand(
        `config instance`,
        `\\$system PRIVATE_deploy_ai_model ${jsonStr}`,
      );
    }

    return isAiModelsReady;
  }
}

/**
 * The Mocked Device implementation is an MQTT client written in Python
 * which mimmicks the behavior of a physical camera device.
 */
export class MockedDevice implements DeviceManager {
  port: number;
  logFile: string;
  ECIfVersion: number;
  configPath: string;
  sampleFiles: { [key: string]: string } = mockedSampleFiles;

  private proc: BackgroundProcess;

  constructor(
    port: number,
    logsDir: string,
    ECIfVersion: number,
    configPath: string,
  ) {
    this.port = port;
    this.logFile = resolve(join(logsDir, `device_${this.port}.log`));
    this.ECIfVersion = ECIfVersion;
    this.configPath = configPath;

    // The mocked device implementation is installed in the virtualenv.
    if (!process.env['VIRTUAL_ENV']) {
      throw new Error(
        'Cannot determine location of mocked device installation. Please activate the venv.',
      );
    }

    this.proc = new BackgroundProcess({
      command: pythonPath,
      args: [
        '-m',
        'mocked_device',
        '--port',
        String(this.port),
        '--version',
        String(this.ECIfVersion),
      ],
      expectedStartString: 'Handshake made',
      outputFile: this.logFile,
    });
  }

  async runLCCommand(
    lc_command: string,
    lc_command_args: string,
  ): Promise<void> {
    const idPrelude = `--port ${this.port}`;
    await runLCCommand(
      `--config-dir ${this.configPath} ${lc_command} ${idPrelude} ${lc_command_args}`,
    );
  }

  async start(): Promise<void> {
    // Start the process and wait until we see its start string
    await this.proc.start();
    logservice.log(
      `Mocked v${this.ECIfVersion} device at port ${this.port} is ready`,
    );
  }

  async stop(): Promise<void> {
    await this.proc.stop();
    logservice.log(
      `Mocked device at port ${this.port} stopped successfully and logs saved to ${this.logFile}`,
    );
  }

  async isStatusCorrect(): Promise<boolean> {
    /* Since the mocked device is spawned fresh, assessing state correctness is not necessary */
    return true;
  }

  async getDeviceInfo(): Promise<LocalDevice> {
    const response = await fetchRetry(
      //TODO modularize the WebAPI port here
      `http://localhost:8000/devices/${this.port}`,
      2000,
      3,
    );
    return response.json() as Promise<LocalDevice>;
  }
}
