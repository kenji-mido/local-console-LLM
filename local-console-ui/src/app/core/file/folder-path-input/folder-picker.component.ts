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
import { randomString } from '@app/core/common/random.utils';
import { IconTextComponent } from '../icon-text/icon-text.component';

export interface FolderInformation {
  path: string;
}

@Component({
  selector: 'app-folder-picker',
  templateUrl: './folder-picker.component.html',
  styleUrl: './folder-picker.component.scss',
  standalone: true,
  imports: [IconTextComponent],
})
export class FolderPickerComponent {
  @Input() folderPath: string = 'Not selected';
  @Input() title: string = '';
  @Input() iconUrl: string = '';
  @Input() disabled: boolean = false;
  @Output() folderSelected = new EventEmitter<FolderInformation>();
  @HostBinding('attr.aria-disabled') get disabledAttr() {
    return this.disabled ? true : null;
  }
  @HostBinding('attr.role') role = 'textbox';

  async openFolderPicker() {
    const electron = window;
    const operationId = randomString();
    if (electron.appBridge?.isElectron) {
      // Dynamically import Electron modules only in Electron runtime
      const folderInfo: FolderInformation =
        await electron.appBridge.selectFolder(operationId);

      // folder picker not cancelled
      if (folderInfo.path) {
        this.folderPath = folderInfo.path;
        this.folderSelected.emit(folderInfo);
      }
    } else {
      // For browsers, provide a fallback, like the File System Access API.
      // This is only for completeness purposes, but it will NOT work since the
      // FileSystemAPI doesn't provide full paths, only sandboxed paths.
      try {
        const directoryHandle = await (window as any).showDirectoryPicker();
        if (directoryHandle?.name) {
          this.folderPath = directoryHandle?.name;
          this.folderSelected.emit({
            path: this.folderPath,
          });
        }
      } catch (err) {
        console.error('Folder selection failed:', err);
      }
    }
  }

  reset() {
    this.folderPath = 'Not selected';
  }
}
