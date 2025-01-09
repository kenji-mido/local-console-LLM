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

const { spawn, exec } = require("child_process");
const http = require("http");

function startApp() {
  return new Promise((resolve, reject) => {
    const app = spawn("yarn", ["start"], {
      detached: true,
      stdio: ["ignore", "pipe", "pipe"],
    });

    app.stdout.on("data", (data) => {
      console.log(data.toString().trim()); // Logging output
    });

    app.stderr.on("data", (data) => {
      console.error(data.toString());
    });

    app.on("close", (code) => {
      console.log(`App process exited with code ${code}`);
      reject(new Error("App exited before becoming reachable"));
    });

    app.on("error", (err) => {
      console.error(`App process error: ${err}`);
      reject(err);
    });

    const timeout = setTimeout(reject, 60000);

    function checkServer() {
      http
        .get("http://localhost:4200", (res) => {
          if (res.statusCode === 200) {
            clearTimeout(timeout);
            resolve(app);
          } else {
            console.error("App responded with:", res.statusCode);
            reject();
          }
        })
        .on("error", (err) => {
          console.warn("App not ready yet");
          setTimeout(checkServer, 3000);
        });
    }

    checkServer();
  });
}

function terminateApp(app) {
  process.kill(-app.pid, "SIGTERM"); // Ensure to use -pid to kill the entire process group
  console.log("App process terminated.");
}

function runTests() {
  return new Promise((resolve, reject) => {
    console.log(`Running tests against localhost:4200`);
    const tests = exec(
      "CONSOLE_BASE_URL=http://localhost:4200 npx playwright test",
    );

    tests.stdout.on("data", (data) => {
      console.log(data.toString().trim());
    });

    tests.stderr.on("data", (data) => {
      console.error(data.toString());
    });

    tests.on("close", (code) => {
      if (code == 0) {
        resolve();
      } else {
        reject(`Tests finished with code ${code}`);
      }
    });

    tests.on("error", (err) => {
      console.error(`Test process error: ${err}`);
      reject(err);
    });
  });
}

startApp()
  .then((app) => {
    runTests()
      .then(() => {
        terminateApp(app);
        process.exit(0);
      })
      .catch((err) => {
        console.error(`Error running tests: ${err}`);
        terminateApp(app);
        process.exit(1);
      });
  })
  .catch((err) => {
    console.error(`Failed to start app: ${err}`);
  });
