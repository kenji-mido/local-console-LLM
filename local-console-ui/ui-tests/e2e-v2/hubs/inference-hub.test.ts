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

import { expect, Page } from '@playwright/test';
import { promises as fs } from 'fs';
import { PNG } from 'pngjs';
import { ssim } from 'ssim.js';

import { DeploymentStatusOut } from '@app/core/deployment/deployment';
import { test, TestBase } from '../../e2e-fixtures/fixtures';
import { checkClassificationInf, checkDetectionInf } from '../../tools/checks';
import { AsSSIMObj, BBoxesForComparison } from '../../tools/image';
import {
  loadFileIntoFileInput,
  selectDefaultDevice,
} from '../../tools/interactions';

const deployAppAndModel = async (
  page: Page,
  fixture: TestBase,
  app_type: string,
): Promise<void> => {
  await page.goto('http://localhost:4200/');
  await page.getByRole('link', { name: 'Deployment' }).click();
  await selectDefaultDevice(page);
  const devicePort: number = 1883;

  // Select AI model and WASM app
  await loadFileIntoFileInput(
    page,
    `samples/${fixture.devices[devicePort].sampleFiles[`${app_type}Model`]}`,
    page.getByTestId('model-selector'),
  );
  await loadFileIntoFileInput(
    page,
    `samples/${fixture.devices[devicePort].sampleFiles[`${app_type}App`]}`,
    page.getByTestId('app-selector'),
  );
  // Deploy
  await page.getByRole('button', { name: 'Deploy' }).click();

  await expect(page.locator('tbody')).not.toBeEmpty();

  await expect(page.locator('tbody')).not.toContainText(
    DeploymentStatusOut.Running,
    { timeout: 0 },
  );

  // Confirm deploy
  await expect(
    page.locator('app-deployment-list').locator('tbody'),
  ).toContainText(DeploymentStatusOut.Success);
};

test.describe(
  'Inference Hub',
  {
    annotation: {
      type: 'Inference Hub',
      description:
        'This test suit covers all E2E (FrontEnd + BackEnd) tests involving the Data Hub tab',
    },
  },
  () => {
    test.beforeEach(async ({ fixture }) => {
      await fixture.waitForDeviceReady(
        Object.keys(fixture.devices).map(Number)[0],
      );
    });
    test.describe(
      'Happy paths',
      {
        annotation: {
          type: 'Happy paths',
          description:
            'These tests showcase normal operation, when usage is correct, leading to successful outcomes',
        },
      },
      () => {
        /**
         * The inference payloads used for comparison are read off the
         * sources of the mocked device via the following python session:
         *
         *  $ python
         *  Python 3.11.11 (main, Dec  4 2024, 08:55:07) [GCC 11.4.0] on linux
         *  ...
         *  >>> import json
         *  >>> from base64 import b64decode
         *  >>> from pathlib import Path
         *  >>>
         *  >>> from local_console.core.camera.flatbuffers import flatbuffer_binary_to_json
         *  >>> from mocked_device.mock.rpc.streaming.fake import get_inference, AppStates
         *  >>>
         *  >>> tmap = {AppStates.Classification: Path('./local-console/src/local_console/assets/schemas/classification.fbs'),
         *              AppStates.Detection:      Path('./local-console/src/local_console/assets/schemas/objectdetection.fbs')}
         *  >>> inference_for = lambda kind: json.dumps(flatbuffer_binary_to_json(tmap[kind].resolve(), b64decode(get_inference(kind).encode())))
         *  >>>
         *  >>> inference_for(AppStates.Classification)
         *  '{"perception": {"classification_list": [...]}}'
         *  >>> inference_for(AppStates.Detection)
         *  '{"perception": {"object_detection_list": [...]}}'
         */

        test.fixme(
          'Inference with the classification model',
          {
            annotation: {
              type: 'Inference with the classification model and PPL param files, but no labels',
              description:
                'This test tries deploys the classification AI model and an associated Edge App. Then it runs inference and compares the JSON inference output and the change of displayed image.',
            },
          },
          async ({ page, fixture }, testInfo) => {
            const devicePort: number = 1883;

            await deployAppAndModel(page, fixture, 'classification');
            await expect(
              page
                .locator('app-deployment-list')
                .locator('td:nth-child(2)')
                .first(),
            ).toContainText('Default');

            // Now go to the Data Hub
            await page.getByRole('link', { name: 'Inference' }).click();
            await selectDefaultDevice(page);

            // Select type of inference model
            await page.getByTestId('ai-model-type-selector').click();
            await page
              .locator('mat-option', { hasText: 'Brain Builder Classifier' })
              .click();

            // Set PPL parameters
            await loadFileIntoFileInput(
              page,
              'samples/configuration_class.json',
              page.getByTestId('ppl-file-select-btn'),
            );

            // Get image display area
            const image = page.locator('app-device-visualizer');

            // Do a shot of it before starting stream
            let ScnPre = await image.screenshot({ timeout: 2000 });
            await fs.writeFile(
              testInfo.outputPath('pre-stream-start.png'),
              ScnPre,
            );
            const PNGpre = PNG.sync.read(ScnPre);

            // Start inference
            await page.getByTestId('apply-configuration').click();
            await page.getByTestId('start-inference-btn').click();

            // Verify decoded JSON inference data
            await page
              .locator('app-inference-display')
              .locator('button', { hasText: 'Json' }) // matching is case-insensitive
              .click();
            const JSONcontents = page.locator('app-inference-display');
            // Give it time to load and render the inference data.
            // The extra timeout is needed due to the device's response time
            await expect(JSONcontents).toContainText('perception', {
              timeout: 10000,
            });

            // Get the rendered inference data
            const rows =
              await JSONcontents.locator('span > .content').allInnerTexts();
            const objDOM = checkClassificationInf(
              fixture.devices[devicePort],
              rows,
            );
            // Do a shot of image display area after starting stream
            let ScnPost = await image.screenshot({ timeout: 2000 });
            await fs.writeFile(
              testInfo.outputPath('post-stream-start.png'),
              ScnPost,
            );
            const PNGpost = PNG.sync.read(ScnPost);

            // Compare the two over the maximal shared bounding box
            const [MinPre, MinPost] = BBoxesForComparison(PNGpre, PNGpost);
            // Get the value of the 'mssim' key via destructuring
            const { mssim } = ssim(AsSSIMObj(MinPre), AsSSIMObj(MinPost));
            // This assertion is simple: the displayed pixels before starting streaming
            // must be **very different** to those after starting the streaming.
            await expect(mssim).toBeLessThan(0.8);
          },
        );

        test.fixme(
          'Inference with the detection model',
          {
            annotation: {
              type: 'Inference with the detection model with PPL parameters file, but no labels',
              description:
                'This test tries deploys the detection AI model and an associated Edge App. Then it runs inference and compares the JSON inference output and the change of displayed image.',
            },
          },
          async ({ page, fixture }, testInfo) => {
            const devicePort: number = 1883;

            await deployAppAndModel(page, fixture, 'detection');
            await expect(
              page
                .locator('app-deployment-list')
                .locator('td:nth-child(2)')
                .first(),
            ).toContainText('Default');

            // Now go to the Data Hub
            await page.getByRole('link', { name: 'Inference' }).click();
            await selectDefaultDevice(page);

            // Select type of inference model
            await page.getByTestId('ai-model-type-selector').click();
            await page
              .locator('mat-option', { hasText: 'Brain Builder Detector' })
              .click();

            // Set PPL parameters
            await loadFileIntoFileInput(
              page,
              'samples/configuration_det.json',
              page.getByTestId('ppl-file-select-btn'),
            );

            // Get image display area
            const image = page.locator('app-device-visualizer');

            // Do a shot of it before starting stream
            let ScnPre = await image.screenshot({ timeout: 2000 });
            await fs.writeFile(
              testInfo.outputPath('pre-stream-start.png'),
              ScnPre,
            );
            const PNGpre = PNG.sync.read(ScnPre);

            // Start inference
            await page.getByTestId('apply-configuration').click();
            await page.getByTestId('start-inference-btn').click();

            // Verify decoded JSON inference data
            await page
              .locator('app-inference-display')
              .locator('button', { hasText: 'Json' }) // matching is case-insensitive
              .click();
            const JSONcontents = page.locator('app-inference-display');
            // Give it time to load and render the inference data.
            // The extra timeout is needed due to the device's response time
            await expect(JSONcontents).toContainText('perception', {
              timeout: 10000,
            });

            // Get the rendered inference data
            const rows =
              await JSONcontents.locator('span > .content').allInnerTexts();

            checkDetectionInf(fixture.devices[devicePort], rows);

            // Do a shot of image display area after starting stream
            let ScnPost = await image.screenshot({ timeout: 2000 });
            await fs.writeFile(
              testInfo.outputPath('post-stream-start.png'),
              ScnPost,
            );
            const PNGpost = PNG.sync.read(ScnPost);

            // Compare the two over the maximal shared bounding box
            const [MinPre, MinPost] = BBoxesForComparison(PNGpre, PNGpost);
            // Get the value of the 'mssim' key via destructuring
            const { mssim } = ssim(AsSSIMObj(MinPre), AsSSIMObj(MinPost));
            // This assertion is simple: the displayed pixels before starting streaming
            // must be **very different** to those after starting the streaming.
            await expect(mssim).toBeLessThan(0.8);
          },
        );

        test(
          'Given User selects a device and an Operation Mode, ' +
            'When User goes to another HUB, goes back to Inference HUB and selects same device ' +
            'Then Same Operation Mode is selected.',
          async ({ page, fixture }) => {
            test.skip(
              fixture.ECIfVersion != 1,
              'FIXME: only for v1 for the moment (v2 configuration impl missing)',
            );

            await page.goto('http://localhost:4200/');
            await page.getByRole('link', { name: 'Inference' }).click();

            for (let [mode, configuration_file] of [
              ['Brain Builder Classifier', 'samples/configuration_class.json'],
              ['Brain Builder Detector', 'samples/configuration_det.json'],
              ['Image Capture', null],
            ]) {
              // Select a device
              await page.getByTestId('device-selector-btn').click();
              await page.getByTestId('device-selector-option-0').click();
              await page.getByRole('button', { name: 'Select' }).click();

              // Select mode
              await page.getByTestId('ai-model-type-selector').click();
              await page.locator('mat-option', { hasText: mode! }).click();

              if (configuration_file)
                await loadFileIntoFileInput(
                  page,
                  configuration_file,
                  page.getByTestId('ppl-file-select-btn'),
                );

              // Apply
              await expect(
                page.getByTestId('apply-configuration'),
              ).toBeEnabled();
              await page.getByTestId('apply-configuration').click();

              // Move to another HUB
              await page.getByRole('link', { name: 'Devices' }).click();

              // Move to Inference HUB
              await page.getByRole('link', { name: 'Inference' }).click();

              // Select device
              await page.getByTestId('device-selector-btn').click();
              await page.getByTestId('device-selector-option-0').click();
              await page.getByRole('button', { name: 'Select' }).click();

              // Mode is the one applied
              await expect(
                page.getByTestId('ai-model-type-selector'),
              ).toContainText(mode!);
            }
          },
        );
      },
    );

    test.describe(
      'Sad paths',
      {
        annotation: {
          type: 'Sad paths',
          description:
            'These tests cover situations leading to errors due to improper usage of the app, to ensure they are properly handled',
        },
      },
      () => {
        test.fixme(
          'Inference without model/app nor labels/PPL param files',
          {
            annotation: {
              type: 'Inference without model/app nor labels. PPL Params added to allow Apply/Start to be enabled',
              description:
                'This test tries running a inference without deploying neither an AI model, an Edge App, a Labels file, nor a PPL param file, which should lead to the inference failing.',
            },
          },
          async ({ page, fixture }) => {
            await page.goto('http://localhost:4200/data-hub');
            await selectDefaultDevice(page);

            // Select type of inference model
            await page.getByTestId('ai-model-type-selector').click();
            await page
              .locator('mat-option', { hasText: 'Brain Builder Classifier' })
              .click();

            // Set PPL parameters
            await loadFileIntoFileInput(
              page,
              'samples/configuration_class.json',
              page.getByTestId('ppl-file-select-btn'),
            );

            await page.getByTestId('apply-configuration').click();
            await page.getByTestId('start-inference-btn').click();
            await expect(
              page.locator('.cdk-dialog-container'),
              'After trying to run inference, a pop up should be visible.',
            ).toBeVisible({ timeout: 100000 });
            await expect(
              page.getByTestId('alert-dialog-title'),
              'The alert dialog title should be visible.',
            ).toBeVisible();
            await expect(
              page.getByText('The device failed to produce'),
              "An error message containing 'The device failed to produce' should appear.",
            ).toBeVisible();
            await page.getByRole('button', { name: 'OK' }).click();
          },
        );

        test.fixme(
          'Inference without model/app but with label and PPL param files',
          {
            annotation: {
              type: 'Inference without model/app with label and PPL param files',
              description:
                'This test tries running a inference having deployed both an AI Model and an Edge App, but without a Labels file, nor a PPL param file, which should lead to the inference failing.',
            },
          },
          async ({ page, fixture }) => {
            await page.goto('http://localhost:4200/data-hub');
            await selectDefaultDevice(page);

            // Select type of inference model
            await page.getByTestId('ai-model-type-selector').click();
            await page
              .locator('mat-option', { hasText: 'Brain Builder Classifier' })
              .click();

            await loadFileIntoFileInput(
              page,
              'samples/labels.txt',
              page.getByTestId('label-file-select-btn'),
            );
            await loadFileIntoFileInput(
              page,
              'samples/configuration_class.json',
              page.getByTestId('ppl-file-select-btn'),
            );
            await page.getByTestId('apply-configuration').click();

            await page.getByTestId('start-inference-btn').click();
            await expect(
              page.locator('.cdk-dialog-container'),
              'After trying to run inference, a pop up should be visible.',
            ).toBeVisible({ timeout: 100000 });
            await expect(
              page.getByTestId('alert-dialog-title'),
              'The alert dialog title should be visible.',
            ).toBeVisible();
            await expect(
              page.getByText('The device failed to produce'),
              "An error message containing 'The device failed to produce' should appear.",
            ).toBeVisible();
            await page.getByRole('button', { name: 'OK' }).click();
          },
        );
      },
    );
  },
);
