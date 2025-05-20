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

import { FileInformationEvented } from '@app/core/file/file-input/file-input.component';

export namespace Files {
  export function sample(
    path: string,
    contents: string = 'My content',
    sideloaded = false,
  ) {
    const encoder = new TextEncoder();
    const parts = path.split('/');
    return <FileInformationEvented>{
      path: path,
      basename: parts[parts.length - 1], // Assume tests don't get run on Windows
      data: encoder.encode(contents),
      sideloaded: sideloaded,
    };
  }
}
