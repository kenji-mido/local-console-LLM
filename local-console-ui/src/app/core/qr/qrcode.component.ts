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
  Input,
  Output,
  EventEmitter,
  ElementRef,
  ViewChild,
} from '@angular/core';
import { downloadFile } from '../common/file.utils';
import { MatIconModule } from '@angular/material/icon';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-qrcode',
  templateUrl: './qrcode.component.html',
  styleUrls: ['./qrcode.component.scss'],
  standalone: true,
  imports: [MatIconModule, CommonModule],
})
export class QrcodeComponent {
  @Input() qrImage?: string;
  @Input() qrExpiredDate?: Date;
  @Output() qrClose = new EventEmitter();
  qrImageLevel: number = 3;
  qrImageLevelMin: number = 0;
  qrImageLevelMax: number = 6;
  qrBodyClass: string = 'qr-body-' + this.qrImageLevel;
  theme = 'light';

  @ViewChild('qrImageDiv') qrImageDiv!: ElementRef<HTMLElement>;

  fullScreen() {
    this.qrBodyClass = 'qr-body-full';
    if (this.qrImageDiv.nativeElement.requestFullscreen) {
      this.qrImageDiv.nativeElement.requestFullscreen();
    }
  }

  zoomOut() {
    if (this.qrImageLevel < this.qrImageLevelMax) {
      this.qrImageLevel++;
    }
    this.qrBodyClass = 'qr-body-' + this.qrImageLevel;
  }

  zoomIn() {
    if (this.qrImageLevel > this.qrImageLevelMin) {
      this.qrImageLevel--;
    }
    this.qrBodyClass = 'qr-body-' + this.qrImageLevel;
  }

  saveQrImage() {
    if (this.qrImage) {
      downloadFile(this.qrImage, 'qrcode.png');
    }
  }

  printQr() {
    window.print();
  }

  closeQr() {
    this.qrClose.emit(true);
  }
}
