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

// https://github.com/microsoft/playwright/issues/20104
export class logservice {
  private static formatMessage(level: string, message: string): string {
    const timestamp = new Date().toISOString();
    return `[${timestamp}] [${level}] ${message}`;
  }

  static debug(message: string): void {
    process.stdout.write(logservice.formatMessage('debug', message) + '\n');
  }

  static log(message: string): void {
    process.stdout.write(logservice.formatMessage('log', message) + '\n');
  }

  static info(message: string): void {
    process.stdout.write(logservice.formatMessage('info', message) + '\n');
  }

  static warn(message: string): void {
    process.stdout.write(logservice.formatMessage('warn', message) + '\n');
  }

  static error(message: string): void {
    process.stderr.write(logservice.formatMessage('error', message) + '\n');
  }
}
