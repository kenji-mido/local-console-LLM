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
  HostListener,
  Input,
  Output,
  ViewChild,
} from '@angular/core';
import { LcDateTimePipe } from '../common/date';
import { downloadFile } from '../common/file.utils';

const QR_IMAGE_LEVEL_MIN = 0;
const QR_IMAGE_LEVEL_MAX = 6;

@Component({
  selector: 'app-qrcode',
  templateUrl: './qrcode.component.html',
  styleUrls: ['./qrcode.component.scss'],
  standalone: true,
  imports: [LcDateTimePipe],
})
export class QrcodeComponent {
  @Input() qrImage?: string;
  @Input() qrExpiredDate?: Date;
  @Output() qrClose = new EventEmitter();
  qrImageLevel: number = 3;
  fullScreen = false;
  theme = 'light';

  @ViewChild('qrWrapper') qrWrapper!: ElementRef<HTMLElement>;

  @HostListener('document:fullscreenchange', ['$event'])
  leaveFullScreen(event: Event) {
    if (!document.fullscreenElement) {
      this.fullScreen = false;
    }
  }

  enterFullScreen() {
    this.fullScreen = true;
    if (this.qrWrapper.nativeElement.requestFullscreen) {
      this.qrWrapper.nativeElement.requestFullscreen();
    }
  }

  zoomIn() {
    if (this.qrImageLevel < QR_IMAGE_LEVEL_MAX) {
      this.qrImageLevel++;
    }
  }

  zoomOut() {
    if (this.qrImageLevel > QR_IMAGE_LEVEL_MIN) {
      this.qrImageLevel--;
    }
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
