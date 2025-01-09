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

const fs = require("fs");
const path = require("path");

// Paths
const outputDir = path.resolve(__dirname, "../dist/local-console-ui/browser");
const errorPagePath = path.join(outputDir, "error-page.html");

const files = fs.readdirSync(outputDir);
// console.log('Files in output directory:', files);

// Find the hashed CSS file in the output directory
const cssFile = files.find(
  (file) => file.startsWith("styles") && file.endsWith(".css"),
);

if (!cssFile) {
  console.error("CSS file not found in output directory");
  process.exit(1);
}

// Create the CSS link tag to inject
const cssLinkTag = `<link rel="stylesheet" href="./${cssFile}">`;

// Read the error page
let errorPageContent = fs.readFileSync(errorPagePath, "utf8");

// Inject the CSS link tag into <head>
errorPageContent = errorPageContent.replace(
  '<link rel="stylesheet" href="./styles.css" data-inject-here />',
  cssLinkTag,
);

// Write the modified error-page.html with the injected CSS link
fs.writeFileSync(errorPagePath, errorPageContent);
console.log(`Injected CSS file (${cssFile}) into error-page.html`);
