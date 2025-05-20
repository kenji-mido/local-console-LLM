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
import { Component, Input, SimpleChanges } from '@angular/core';
import { LocalDevice } from '@app/core/device/device';
import {
  SysAppModuleStateAiModelV2,
  isSysModuleConfig,
} from '@app/core/module/sysapp';

interface AIModelInfoTabItems {
  model_id: string | undefined;
  version: string | undefined;
  conv_version: string | undefined;
}

@Component({
  selector: 'app-aimodel-info',
  templateUrl: './aimodel-info.component.html',
  styleUrls: ['./aimodel-info.component.scss'],
  standalone: true,
  imports: [CommonModule],
})
export class AIModelInfo {
  aimodels_info: AIModelInfoTabItems[] = [];
  num_models: number[] = [];

  @Input() device: LocalDevice | null = null;

  ngOnChanges(changes: SimpleChanges) {
    this.onDeviceInfoReceived(changes['device'].currentValue);
  }
  onDeviceInfoReceived(device: LocalDevice | null) {
    this.aimodels_info = [];
    this.num_models = [];
    let i = 1;
    if (
      device === null ||
      device.modules === null ||
      !isSysModuleConfig(device.modules?.[0].property.configuration) ||
      device.modules?.[0].property.configuration!.device_info?.ai_models ===
        undefined
    ) {
      this.aimodels_info = [
        {
          model_id: undefined,
          version: undefined,
          conv_version: undefined,
        },
      ];
      this.num_models.push(i);
      i += 1;
      return;
    }
    const ai_models: SysAppModuleStateAiModelV2[] =
      device.modules?.[0].property.configuration!.device_info?.ai_models;
    for (var ai_model of ai_models) {
      this.aimodels_info.push({
        model_id: ai_model.name,
        version: ai_model.version,
        conv_version: ai_model.converter_version,
      });
      this.num_models.push(i);
      i = i + 1;
    }
  }
}
