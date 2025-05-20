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

process.once("loaded", () => {
  const { contextBridge, ipcRenderer } = require("electron");

  const bridge = {
    isElectron: true,

    selectFolder: async (operationId) => {
      ipcRenderer.send("select-folder", operationId);
      return new Promise((resolve) => {
        ipcRenderer.once(`selected-folder-${operationId}`, (event, path) => {
          resolve(path);
        });
      });
    },

    selectFile: async (filterName, acceptedExtensions, operationId) => {
      ipcRenderer.send(
        "select-file",
        filterName,
        acceptedExtensions,
        operationId,
      );
      return new Promise((resolve) => {
        ipcRenderer.once(`selected-file-${operationId}`, (event, fileInfo) => {
          resolve(fileInfo);
        });
      });
    },

    readFile: async (path) => {
      ipcRenderer.send("read-file", path);
      return new Promise((resolve) => {
        ipcRenderer.once("read-file-return", (event, fileInfo) => {
          resolve(fileInfo);
        });
      });
    },
  };

  contextBridge.exposeInMainWorld("appBridge", bridge);
});
