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

import {
  Component,
  EventEmitter,
  HostBinding,
  Input,
  Output,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatInputModule } from '@angular/material/input';
import { randomString } from '@app/core/common/random.utils';
import { IconTextComponent } from '../icon-text/icon-text.component';

export interface FileInformation {
  path: string;
  basename: string;
  data: Uint8Array;
}

export interface FileInformationEvented extends FileInformation {
  sideloaded: boolean;
}

@Component({
  selector: 'app-file-input',
  templateUrl: './file-input.component.html',
  styleUrl: './file-input.component.scss',
  standalone: true,
  imports: [IconTextComponent, MatInputModule, FormsModule],
})
export class FileInputComponent {
  filename: string = 'Not selected';
  @Input() title: string = '';
  @Input() iconUrl: string = '';
  @Input() iconButton = '';
  @Input() required = false;
  @Input() disabled = false;
  @Output() fileSelected = new EventEmitter<FileInformationEvented>();
  // comma-separated list of period-prefixed extensions to accept
  @Input() extensions: string = '*';
  @HostBinding('attr.aria-disabled') get disabledAttr() {
    return this.disabled ? true : null;
  }
  @HostBinding('attr.role') role = 'textbox';
  private path?: string;

  async openFilePicker() {
    const operationId = randomString();
    const electron = window;
    if (electron.appBridge?.isElectron) {
      // Dynamically import Electron modules only in Electron runtime
      const fileInfo: FileInformation = await electron.appBridge.selectFile(
        this.title,
        this.extensions.split(',').map((e) => e.replace('.', '')),
        operationId,
      );
      this.__sendEvent(fileInfo, false);
    } else {
      await this.__provideFallback();
    }
  }

  async sideloadFile(path: string | null) {
    if (path === null) {
      await this.reset();
      return;
    }

    const electron = window;
    if (electron.appBridge?.isElectron) {
      // Dynamically import Electron modules only in Electron runtime
      const fileInfo: FileInformation = await electron.appBridge.readFile(path);
      this.__sendEvent(fileInfo, true);
    } else {
      this.__provideFallback();
    }
  }

  async reset() {
    this.filename = 'Not selected';
    this.path = undefined;
  }

  private __sendEvent(fileInfo: FileInformation, sideloaded = false) {
    // Only send event if truly changed
    // (emulating same behavior as <input type='file' />)

    // file picker cancelled
    if (!fileInfo.path || !fileInfo.basename || !fileInfo.data) return;
    if (fileInfo && fileInfo.path !== this.path) {
      this.path = fileInfo.path;
      this.filename = fileInfo.basename;
      this.fileSelected.emit(<FileInformationEvented>{
        ...fileInfo,
        sideloaded,
      });
    }
  }

  private async __provideFallback() {
    // This is only for completeness purposes, but it will NOT work with the real backend
    // since the FileSystemAPI doesn't provide full paths, only sandboxed paths.
    // Used only for testing
    console.warn('Mocking full-path file selection');
    const cleanExt = this.extensions.split(',').map((e) => e.replace('.', ''));
    let types: FilePickerAcceptType[] = [];

    if (!cleanExt.includes('*')) {
      cleanExt.forEach((ext) =>
        types.push({
          accept: {
            'application/octet-stream': [('.' + ext) as '.${string}'],
          },
        }),
      );
    }
    const files = await window.showOpenFilePicker({
      types,
      multiple: false,
    });
    if (files) {
      const file = files[0];
      const fileData = await file.getFile();
      const arrayBuffer = await fileData.arrayBuffer();
      const uint8Array = new Uint8Array(arrayBuffer);
      this.__sendEvent(
        {
          path: '/path/to/nowhere/' + file.name,
          basename: file.name,
          data: uint8Array,
        },
        true,
      );
    }
  }
}
