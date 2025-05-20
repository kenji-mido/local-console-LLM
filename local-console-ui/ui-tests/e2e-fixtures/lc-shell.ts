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
import { exec } from 'child_process';
import { join } from 'path';
import { logservice } from '../tools/logservice';

const isWindows = process.platform === 'win32';

// The local console server implementation is installed in the virtualenv.
if (!process.env['VIRTUAL_ENV']) {
  throw new Error(
    'Cannot determine location of local console installation. Please activate the venv.',
  );
}
export const pythonPath: string = join(
  process.env['VIRTUAL_ENV'] || '',
  isWindows ? 'Scripts\\python.exe' : 'bin/python',
);

export async function fetchRetry(
  url: string,
  delay: number,
  tries: number,
): Promise<Response> {
  async function onError(err: Error) {
    const triesLeft = tries - 1;
    if (!triesLeft) {
      throw Error('Local Console requests has failed');
    }
    return waitFor(delay).then(() => fetchRetry(url, delay, triesLeft));
  }
  return fetch(url).catch(onError);
}

export async function runLCCommand(lc_command_args: string): Promise<void> {
  const composedCommand = [
    pythonPath,
    '-m',
    'local_console ' + lc_command_args,
  ].join(' ');
  return new Promise((resolve, reject) => {
    exec(composedCommand, (error, stdout, stderr) => {
      if (error) {
        logservice.log(`Error executing command: ${error.message}`);
        logservice.log(`Exit code: ${error.code}`);
        reject(error);
        if (stderr) {
          logservice.log(`stderr: ${stderr}`);
        }
        return;
      }
      resolve();
    });
  });
}

export function formatAsCommand(object: object) {
  const jsonStr = isWindows
    ? formatForWindowsCommand(object)
    : formatForLinuxCommand(object);
  return jsonStr;
}

function formatForWindowsCommand(object: object) {
  let str = JSON.stringify(object);

  // Escape characters for PowerShell
  str = str
    .replace(/\\/g, '\\\\') // Escape backslashes
    .replace(/"/g, '\\"') // Escape double quotes
    .replace(/\$/g, '\\$'); // Escape dollar sign ($), as it's special in PowerShell
  return `${str}`;
}

function formatForLinuxCommand(object: object) {
  let str = JSON.stringify(object);
  return `'${str}'`;
}
