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

const { spawn, execSync, exec } = require("child_process");
const http = require("http");

const isWindows = process.platform === "win32";

function startApp() {
  return new Promise((resolve, reject) => {
    const app = spawn("yarn", ["start"], {
      shell: true,
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
  if (isWindows) {
    try {
      execSync(`taskkill /PID ${app.pid} /F /T`);
      console.log("App process terminated.");
    } catch (error) {
      console.error(`Error terminating app: ${error}`);
    }
  } else {
    // Ensure to use -pid to kill the entire process group
    process.kill(-app.pid, "SIGTERM");
    console.log("App process terminated.");
  }
}

function runTests(testType, args) {
  return new Promise((resolve, reject) => {
    console.log(`Running tests against localhost:4200`);

    const ECI_VERSION =
      process.env.ECI_VERSION ?? (testType === "e2e-v2" ? "2" : "1");
    console.debug(`ECI_VERSION=${ECI_VERSION}`);

    if (!["e2e-v2", "frontend"].includes(testType)) {
      console.error(
        "Error in test type; Only values accepted are: 'e2e-v2' and 'frontend'",
      );
      terminateApp(app);
      process.exit(1);
    }
    const outputFolder = "./reports/playwright/" + testType;
    console.info("Output folder", outputFolder);

    const artifactsFolder = "./reports/playwright/artifacts/" + testType;
    console.info("Artifacts folder", outputFolder);

    const tests = exec(
      `npx playwright test --workers 1 --output ${artifactsFolder} ui-tests/${testType} ${args.join(" ")}`,
      {
        env: {
          ...process.env,
          CONSOLE_BASE_URL: "http://localhost:4200",
          PLAYWRIGHT_HTML_OUTPUT_DIR: outputFolder,
          ECI_VERSION,
        },
      },
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
    runTests(process.argv[2], process.argv.slice(3))
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
