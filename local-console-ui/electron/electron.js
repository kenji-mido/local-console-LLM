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
const { spawn } = require("child_process");
const circularBuffer = require("@stdlib/utils-circular-buffer");
const { app, BrowserWindow, screen, ipcMain, dialog } = require("electron");
const path = require("path");
const { readFile } = require("node:fs/promises");

// force `$USERDATA/local-console` instead of `$USERDATA/local-console-ui`
// https://www.electronjs.org/docs/latest/api/app#appgetpathname:
// - userData is by default appData appended by app name
app.setPath("userData", path.resolve(app.getPath("appData"), "local-console"));

const log = require("electron-log");

log.initialize();
log.transports.console.level = false;
log.transports.file.level = "debug";
log.eventLogger.startLogging();
log.errorHandler.startCatching();
log.info("platform:", process.platform);
log.info("exe:", app.getPath("exe"));
log.info("appData:", app.getPath("appData"));
log.info("userData:", app.getPath("userData"));
log.info("module:", app.getPath("module"));
log.info("environ:", process.env);

let mainWindow;
let backend;
let backendIsClosedResolve;
let backendIsClosed = new Promise((resolve) => {
  backendIsClosedResolve = resolve;
});

// Backend process management objects
let shutdownIsOrderly = false;
const errorLogQueueCapacity = 100;
let errorLogQueue = new circularBuffer(errorLogQueueCapacity);

const getRunPath = () => {
  let backendPath;
  if (["linux", "darwin"].includes(process.platform)) {
    log.info(process.env["APPIMAGE"]);
    // This assumes invocation from a shell where
    // the virtualenv has been activated.
    if (!process.env["VIRTUAL_ENV"]) {
      throw new Error(
        "Cannot determine location of backend. Please activate the venv.",
      );
    }
    backendPath = path.join(process.env["VIRTUAL_ENV"], "bin", "local-console");
  } else if (process.platform === "win32") {
    if (process.env["VIRTUAL_ENV"]) {
      backendPath = path.join(
        process.env["VIRTUAL_ENV"],
        "Scripts",
        "local-console.exe",
      );
    } else {
      let installPath = path.dirname(app.getPath("exe"));

      // This matches the directory layout created by:
      // - ./inno-setup.iss at line 38
      // - ./local-console/windows/utils.ps1 at line 140
      // - ./local-console/windows/steps/app.ps1 at line 41
      let base = path.resolve(path.dirname(installPath));
      backendPath = path.join(
        base,
        "virtualenv",
        "Scripts",
        "local-console.exe",
      );
    }
  } else {
    throw new Error("Unsupported platform", process.platform);
  }

  return backendPath;
};

const startBackend = () => {
  const bypassBackend = "_LC_NO_BACKEND" in process.env;
  log.warn("Bypass Backend? " + bypassBackend ? "yes" : "no");
  let backendProcess;

  if (!bypassBackend) {
    const backendPath = getRunPath();
    log.info(backendPath);
    backendProcess = spawn(backendPath, ["-v", "serve"]);
  } else {
    const shell = process.platform === "win32" ? "powershell.exe" : "/bin/sh";
    const command = process.platform === "win32" ? "sleep" : "sleep 100000";
    backendProcess = spawn(command, { shell });
  }

  backendProcess.stdout.on("data", (data) => {
    log.log(`stdout:\n${data}`);
  });
  backendProcess.stderr.on("data", (data) => {
    log.log(`stderr: ${data}`);
    if (data.indexOf("ERROR") != -1) {
      errorLogQueue.push(`${data}`);
    }
  });

  backendProcess.on("message", (message) => {
    log.log(`message:\n${message}`);
  });
  backendProcess.on("error", (error) => {
    let msg = `error: ${error.message}`;
    log.log(msg);
    errorLogQueue.push(msg);
  });

  return backendProcess;
};

function createWindow() {
  const size = screen.getPrimaryDisplay().workAreaSize;
  const mainWindow = new BrowserWindow({
    center: true,
    width: Math.max(1000, Math.round(0.7 * size.width)),
    height: Math.max(800, Math.round(0.7 * size.height)),
    webPreferences: {
      nodeIntegration: true,
      preload: path.resolve(app.getAppPath(), "electron/setupBridge.js"),
    },
    autoHideMenuBar: true,
    icon: path.join(
      app.getAppPath(),
      `/dist/local-console-ui/browser/icon.png`,
    ),
  });

  mainWindow.loadFile(
    path.join(app.getAppPath(), `/dist/local-console-ui/browser/index.html`),
  );

  mainWindow.on("close", (e) => {
    e.preventDefault();
    let is_alive = backend && backend.exitCode === null;
    log.debug(
      "Processing window close. Is backend alive?: " +
        (is_alive ? "yes" : "no"),
    );
    if (is_alive) {
      shutdownIsOrderly = true;
      backend.stdin.write("shutdown\n");
    }
    mainWindow.destroy();
  });

  // Listen for F12 key to open/close dev tools
  mainWindow.webContents.on("before-input-event", (event, input) => {
    if (input.key === "F12" && input.type === "keyDown") {
      if (mainWindow.webContents.isDevToolsOpened()) {
        mainWindow.webContents.closeDevTools();
      } else {
        mainWindow.webContents.openDevTools();
      }
    }
  });

  return mainWindow;
}

// Handle the 'select-folder' event
ipcMain.on("select-folder", async (event, operationId) => {
  // Attach dialog to window gives focus:
  // https://github.com/electron/electron/issues/10723#issuecomment-450304974
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ["openDirectory"],
  });
  if (!result.canceled) {
    event.sender.send(`selected-folder-${operationId}`, {
      path: result.filePaths[0],
    });
  } else {
    event.sender.send(`selected-folder-${operationId}`, { path: null });
  }
});

// Handle the 'select-file' event
ipcMain.on(
  "select-file",
  async (event, filterName, acceptedExtensions, operationId) => {
    controller = new AbortController();
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ["openFile"],
      filters: [{ name: filterName, extensions: acceptedExtensions }],
    });
    const filepath = result.canceled ? null : result.filePaths[0];
    const name = result.canceled ? null : path.basename(filepath);
    const content = result.canceled ? null : await readFile(filepath);
    event.sender.send(`selected-file-${operationId}`, {
      path: filepath,
      basename: name,
      data: content,
    });
  },
);

// Handle the 'read-file' event
ipcMain.on("read-file", async (event, filepath) => {
  const name = path.basename(filepath);
  const content = await readFile(filepath);
  event.sender.send("read-file-return", {
    path: filepath,
    basename: name,
    data: content,
  });
});

app.whenReady().then(() => {
  backend = startBackend();
  mainWindow = createWindow();

  backend.on("close", (code, signal) => {
    log.log(`child process close'd with code ${code} and signal ${signal}`);
    backendIsClosedResolve();

    if (!shutdownIsOrderly) {
      const path_page = path.join(
        app.getAppPath(),
        `/dist/local-console-ui/browser/error-page.html`,
      );
      const message = encodeURIComponent(errorLogQueue.toArray().join("\n"));
      mainWindow.loadURL(`file://${path_page}?message=${message}`);
    }
  });

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      mainWindow = createWindow();
    }
  });
});

app.on("window-all-closed", async () => {
  log.info("Electron is quitting...");
  await backendIsClosed;
  log.info("Backend is closed");
  if (process.platform !== "darwin") {
    app.quit();
  }
});
