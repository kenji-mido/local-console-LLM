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

import { CommonModule } from '@angular/common';
import { Component, Directive, Input } from '@angular/core';
import { MatTooltipModule } from '@angular/material/tooltip';

@Component({
  selector: 'app-infotip',
  imports: [MatTooltipModule, CommonModule],
  styles: `
    :host {
      display: flex;
    }
    :host img {
      --info-size: 26px;
      width: var(--info-size);
      height: var(--info-size);
    }
  `,
  template: `
    <img
      src="images/light/info_icon.svg"
      [ngStyle]="{ '--info-size': size + 'px' }"
      [matTooltip]="tip || ''"
    />
  `,
  standalone: true,
})
export class InfotipDirective {
  @Input() tip?: string;
  @Input() size = 26;
}
