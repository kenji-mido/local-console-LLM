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
  ElementRef,
  EventEmitter,
  Input,
  Output,
  ViewChild,
} from '@angular/core';
import { IconTextComponent } from '../icon-text/icon-text.component';
import { MatInputModule } from '@angular/material/input';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-file-input',
  templateUrl: './file-input.component.html',
  styleUrl: './file-input.component.scss',
  standalone: true,
  imports: [IconTextComponent, MatInputModule, FormsModule],
})
export class FileInputComponent {
  @ViewChild('fileInput') fileInput!: ElementRef;

  filename: string = 'Not selected';
  @Input() title: string = '';
  @Input() iconUrl: string = 'images/light/device_item.svg';
  @Input() iconButton = '';
  @Output() fileSelected = new EventEmitter<File>();
  @Input() extension: string = '';

  handleFileSelection(files: FileList | null) {
    if (files && files.length > 0) {
      this.filename = files[0].name;
      this.fileSelected.emit(files[0]);
    }
  }

  async reset() {
    this.filename = 'Not selected';
    // Reset <input> to trigger (change)
    this.fileInput.nativeElement.value = null;
  }
}
