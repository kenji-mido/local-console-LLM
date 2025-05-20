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

import { execSync, spawn, type ChildProcess } from 'child_process';
import { promises as fs, writeFileSync } from 'fs';
import { logservice } from './logservice';

// Maximum time (in milliseconds) allowed for processes to shut down gracefully.
const GRACEFUL_SHUTDOWN_TIMEOUT_MS = 10000;

const isWindows = process.platform === 'win32';

interface BackgroundProcessOptions {
  command: string;
  args?: string[];
  expectedStartString: string; // The special string to wait for in stdout/stderr
  expectedEndString?: string; // The special string to wait for in stdout/stderr
  outputFile: string; // The file where stdout+stderr logs will be saved on stop
  environ?: { [envVar: string]: string };
  useShutdown?: boolean; // Send 'shutdown' through stdin to close process
}

/**
 * A class that runs a background process, waits for a specific
 * line in its stdout,  and provides a stop method to clean up
 * and save logs.
 */
export class BackgroundProcess {
  private command: string;
  private args: string[];
  private environ?: { [envVar: string]: string };
  private outputFile: string;

  private child?: ChildProcess;
  private started: boolean = false;
  private exiting: boolean = false;
  private logBuffer: string = '';

  // For signaling the start of the process
  private expectedStartString: string;
  private startPromise?: Promise<void>;
  private startResolve?: () => void;
  private startReject?: (err: any) => void;

  // For signaling the end of the process
  private expectedEndString?: string;
  private endPromise?: Promise<void>;
  private endResolve?: () => void;
  private endReject?: (err: any) => void;

  // Graceful mode
  private useShutdown: boolean;

  constructor(options: BackgroundProcessOptions) {
    this.command = options.command;
    this.args = options.args || [];
    this.expectedStartString = options.expectedStartString;
    this.expectedEndString = options.expectedEndString;
    this.outputFile = options.outputFile;
    this.environ = options.environ;
    this.useShutdown = options.useShutdown ?? false;
  }

  /**
   * Starts the background process and returns once the expectedStartString is found in stdout.
   * If the process exits before producing the expected line, the promise will reject.
   */
  public async start(): Promise<void> {
    if (this.started) {
      throw new Error('Process is already started');
    }

    // Add optional specified environment variables
    const env = { ...process.env, ...this.environ };
    this.child = spawn(this.command, this.args, { stdio: 'pipe', env });

    // React to stdout and stderr
    this.startPromise = new Promise<void>((resolve, reject) => {
      this.startResolve = resolve;
      this.startReject = reject;
    });

    // Handle process output (stdout + stderr)
    this.child.stdout?.on('data', this.handleOutput.bind(this));
    this.child.stderr?.on('data', this.handleOutput.bind(this));

    // If the process exits before we see the signal, reject the start promise
    this.child.on('exit', (code, signal) => {
      if (this.startReject && !this.started) {
        writeFileSync(this.outputFile, this.logBuffer, 'utf-8');
        this.startReject(
          new Error(
            `Process exited (code=${code}, signal=${signal}) before the expected output was found`,
          ),
        );
        this.startReject = undefined;
      }
    });

    // Wait for start condition to be met
    await this.startPromise;
  }

  /**
   * Handles data from stdout or stderr
   */
  private handleOutput(data: Buffer): void {
    const chunk = data.toString('utf-8');
    this.logBuffer += chunk;
    this.checkOutputAtStart();
    this.checkOutputAtStop();
  }

  /**
   * Checks if the expected start string is in the output.
   * Marks the process as started when found.
   */
  private checkOutputAtStart(): void {
    if (
      !this.started &&
      !this.exiting &&
      this.logBuffer.includes(this.expectedStartString)
    ) {
      this.startResolve?.();
      this.started = true;
      this.startResolve = undefined;
      this.startReject = undefined;
    }
  }

  /**
   * The condition to determine the process as "stopped"
   */
  private checkOutputAtStop(): void {
    if (
      this.started &&
      this.exiting &&
      this.expectedEndString &&
      this.logBuffer.includes(this.expectedEndString)
    ) {
      this.endResolve?.();
      this.started = false;
      this.exiting = false;
      this.endResolve = undefined;
      this.endReject = undefined;
    }
  }

  /**
   * Stops the background process, saves logs to a file, then kills the process if needed.
   * If the process is not running, this will just write whatever was captured.
   */
  public async stop(): Promise<void> {
    this.exiting = true;

    if (this.child && !this.child.killed) {
      try {
        // Attempt graceful shutdown (send 'shutdown' message or SIGTERM)
        this.gracefulShutdown();

        // Wait for process termination or timeout
        await this.waitForTerminationOrForce();
      } catch (error) {
        logservice.error(`Error shutting down: ${error}`);
      }

      // Save the log buffer to the output file
      await fs.writeFile(this.outputFile, this.logBuffer, 'utf-8');
    }
  }

  /**
   * Graceful shutdown the process
   */
  private gracefulShutdown(): void {
    try {
      if (isWindows) {
        if (this.useShutdown) {
          this.child?.stdin?.write('shutdown\n');
          logservice.log(
            `Sent shutdown command to process with PID ${this.child?.pid}.`,
          );
        } else {
          /**
           * Using force because we get the following error:
           *
           * ERROR: The process with PID XXXX could not be terminated.
           * Reason: This process can only be terminated forcefully (with /F option).
           */
          execSync(`taskkill /PID ${this.child?.pid} /T /F`);
          logservice.log(
            `taskkill command to process with PID ${this.child?.pid}.`,
          );
        }
      } else {
        this.child?.kill('SIGTERM');
        logservice.log(`Sent SIGTERM to process with PID ${this.child?.pid}.`);
      }
    } catch (err) {
      logservice.error(
        `Error gracefully killing process with PID ${this.child?.pid}: ${err}`,
      );
    }
  }

  /**
   * Forcefully kills the process
   */
  private forceShutdown(): void {
    try {
      if (isWindows) {
        execSync(`taskkill /PID ${this.child?.pid} /T /F`);
        logservice.log(
          `taskkill command to process with PID ${this.child?.pid}.`,
        );
      } else {
        this.child?.kill('SIGKILL');
        logservice.log(`Sent SIGKILL to process with PID ${this.child?.pid}.`);
      }
    } catch (err) {
      logservice.error(
        `Error forcefully killing process with PID ${this.child?.pid}: ${err}`,
      );
    }
  }

  /**
   * Waits for the process to terminate or forces termination if timeout occurs
   */
  private async waitForTerminationOrForce(): Promise<void> {
    const timeoutPromise = new Promise<void>((resolve) => {
      const timeoutId = setTimeout(() => {
        logservice.log(
          `Timeout reached. Forcing shutdown of process with PID ${this.child?.pid}.`,
        );
        this.forceShutdown();
        resolve();
      }, GRACEFUL_SHUTDOWN_TIMEOUT_MS);

      // Listen for the 'exit' event to cancel timeout
      this.child?.on('exit', (code, signal) => {
        clearTimeout(timeoutId);
        logservice.log(
          `Process with PID ${this.child?.pid} exited (code=${code}, signal=${signal})`,
        );
        resolve();
      });
    });

    await timeoutPromise;
  }
}
