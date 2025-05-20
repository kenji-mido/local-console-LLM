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

import { ScrollingModule } from '@angular/cdk/scrolling';
import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import {
  DeployHistoriesOut,
  DeploymentStatusOut,
} from '@app/core/deployment/deployment';
import { DeploymentService } from '@app/core/deployment/deployment.service';
import { DevicePipesModule } from '@app/core/device/device.pipes';
import { IconTextComponent } from '@app/core/file/icon-text/icon-text.component';
import { FirmwarePipesModule } from '@app/core/firmware/firmware.pipes';
import { FirmwareService } from '@app/core/firmware/firmware.service';
import { ModelService } from '@app/core/model/model.service';
import {
  TableVirtualScrollDataSource,
  TableVirtualScrollModule,
} from 'ng-table-virtual-scroll';

enum ArtifactType {
  EdgeApp = 'Edge App',
  Model = 'AI Model',
  Firmware = 'Firmware',
}

interface DeployHistoryItem {
  start_time: string;
  device_name: string;
  status: string;
  type: string;
  filename: string;
  version: string;
  isNew: boolean; // used to highlight the new elements
}

@Component({
  selector: 'app-deployment-list',
  templateUrl: './deployment-list.component.html',
  styleUrls: ['./deployment-list.component.scss'],
  standalone: true,
  imports: [
    DevicePipesModule,
    ScrollingModule,
    TableVirtualScrollModule,
    FormsModule,
    MatProgressSpinnerModule,
    CommonModule,
    MatTableModule,
    MatButtonModule,
    FirmwarePipesModule,
    IconTextComponent,
  ],
})
export class DeploymentListComponent {
  theme = 'light';
  itemSize = 47;
  itemNumber = 5;
  headerSize = 40;

  displayedColumns: string[] = [
    'start_time',
    'device_name',
    'status',
    'type',
    'filename',
    'version',
  ];

  dataSource: TableVirtualScrollDataSource<DeployHistoryItem> =
    new TableVirtualScrollDataSource<DeployHistoryItem>([]);

  constructor(
    private deploymentService: DeploymentService,
    private modelService: ModelService,
    private firmwareService: FirmwareService,
  ) {
    deploymentService.deployment$
      .pipe(takeUntilDestroyed())
      .subscribe((devices) => this.onDeploymentLoaded(devices));
  }

  getIconStatus(value: DeploymentStatusOut) {
    if (value === DeploymentStatusOut.Success)
      return 'images/' + this.theme + '/status-success.svg';
    if (value === DeploymentStatusOut.Error)
      return 'images/' + this.theme + '/status-error.svg';
    return 'images/' + this.theme + '/deployment_status_deploying.svg';
  }

  getIconType(value: ArtifactType) {
    if (value === ArtifactType.Model)
      return 'images/' + this.theme + '/type_model.svg';
    if (value === ArtifactType.EdgeApp)
      return 'images/' + this.theme + '/type_app.svg';
    return 'images/' + this.theme + '/type_firmware.svg';
  }

  onDeploymentLoaded(deployment: DeployHistoriesOut) {
    let elements: DeployHistoryItem[] = [];
    for (let elem of deployment.deploy_history) {
      let base = {
        start_time: elem.from_datetime,
        device_name: elem.devices[0].device_name,
        isNew: false,
      };
      for (let app of elem.edge_apps ?? []) {
        elements.push({
          ...base,
          type: ArtifactType.EdgeApp,
          status: app.status,
          filename: app.app_name,
          version: app.app_version,
        });
      }
      for (let model of elem.models ?? []) {
        elements.push({
          ...base,
          type: ArtifactType.Model,
          status: model.status,
          filename: this.modelService.getFileName(model.model_id),
          version: '',
        });
      }
      for (let firmware of elem.edge_system_sw_package ?? []) {
        elements.push({
          ...base,
          type: ArtifactType.Firmware,
          status: firmware.status,
          filename: this.firmwareService.getFileName(firmware.firmware_id),
          version: firmware.firmware_version,
        });
      }
    }
    elements.sort((a, b) => b.start_time.localeCompare(a.start_time));
    for (let i = 0; i < elements.length; ++i)
      elements[i].isNew = i < elements.length - this.dataSource.data.length;
    this.dataSource = new TableVirtualScrollDataSource(elements);
  }
}
