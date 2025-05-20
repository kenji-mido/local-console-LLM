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

import { join } from 'path';
import { logservice } from '../tools/logservice';
import { BackgroundProcess } from '../tools/proc-manager';
import { fetchRetry, pythonPath, runLCCommand } from './lc-shell';

/**
 * The following enables tests to request a fresh local console server
 * which is the easiest way to test behavior that is affected by settings
 * that are persisted to the server's configuration file.
 */
export class LocalConsoleServer {
  private proc: BackgroundProcess;
  host: string;
  workDir: string;
  logFile: string;

  constructor(testOutputDir: string, host: string) {
    this.workDir = join(testOutputDir, 'server');
    this.logFile = join(this.workDir, `server.log`);
    this.host = host;

    this.proc = new BackgroundProcess({
      command: pythonPath,
      args: [
        '-m',
        'local_console',
        '--config-dir',
        this.workDir,
        '-v',
        'serve',
      ],
      outputFile: this.logFile,
      // See local-console/src/local_console/fastapi/main.py::lifespan
      expectedStartString: 'Server has started',
      expectedEndString: 'Server has stopped',
      environ: {
        LC_DEFAULT_DIRS_PATH: this.workDir,
      },
      useShutdown: true,
    });
  }

  public async start(): Promise<void> {
    await this.proc.start();
    await this.waitForServerReady();
    logservice.log(
      `Local Console server is ready (config at: ${this.workDir})`,
    );
  }

  public async stop(): Promise<void> {
    await this.proc.stop();
    logservice.log(`Local Console server and logs saved to ${this.logFile}`);
  }

  public async generateConfigJSON(
    deviceId: number,
    ECIfVersion: number,
  ): Promise<void> {
    const commonPath = join(this.workDir, 'local-console', deviceId.toString());
    const prelude = `--config-dir ${this.workDir} config set --port ${deviceId}`;

    await runLCCommand(`${prelude} mqtt.host ${this.host}`);
    await runLCCommand(`${prelude} persist.device_dir_path ${commonPath}`);
    await runLCCommand(`${prelude} onwire_schema EVP${ECIfVersion}`);

    logservice.debug(`JSON configuration has been generated`);
  }

  public getConfigPath() {
    return this.workDir;
  }

  private async waitForServerReady(): Promise<void> {
    const res = await fetchRetry('http://localhost:8000/health', 2000, 3);
    if (res.status === 200) {
      const { status } = await res.json();
      if (status === 'OK') {
        logservice.info('Server is ready.');
        return;
      }
    }

    throw new Error(`Server health check failed. Status=${res.status}.`);
  }
}
