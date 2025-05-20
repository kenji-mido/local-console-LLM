/**
 * Copyright 2025 Sony Semiconductor Solutions Corp.
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

import { Component, TemplateRef, ViewChild } from '@angular/core';
import { Router } from '@angular/router';
import { RoundNumberPipe } from '@app/core/common/number.pipe';
import { randomString } from '@app/core/common/random.utils';
import { InferenceResultsService } from '@app/core/inference/inferenceresults.service';
import {
  NotificationKind,
  NotificationsService,
} from '@app/core/notification/notifications.service';
import { DialogService } from '@app/layout/dialogs/dialog.service';
import { action } from '@app/layout/dialogs/user-prompt/action';
import { InferenceHubRouteParameters } from '@app/layout/pages/data-hub/data-hub.screen';

@Component({
  selector: 'app-device-notifications-handler',
  templateUrl: './device-notifications-handler.component.html',
  standalone: true,
  imports: [RoundNumberPipe],
})
export class DeviceNotificationsHandlerComponent {
  @ViewChild('deviceQuotaHitTpl') deviceQuotaHitTpl!: TemplateRef<any>;

  constructor(
    private prompts: DialogService,
    private router: Router,
    private inferences: InferenceResultsService,
    notifications: NotificationsService,
  ) {
    notifications
      .on(NotificationKind.DEVICE_NO_QUOTA)
      .subscribe(this.handleQuotaHitNotification.bind(this));
  }

  private async handleQuotaHitNotification(data: any) {
    const deviceId = data.device_id;
    this.inferences.teardown(deviceId);
    const result = await this.prompts.prompt({
      message: this.deviceQuotaHitTpl,
      showCancelButton: false,
      title: 'Operation Stopped',
      type: 'error',
      context: data,
      actionButtons: [
        action.weak('close', 'Close'),
        action.weak('goto', 'Storage Settings', 'storage'),
      ],
    });

    if (result?.id === 'goto') {
      this.router.navigate(['/data-hub'], {
        queryParams: <InferenceHubRouteParameters>{
          deviceId: deviceId,
          state: 'quota-hit',
          __rid: randomString(),
        },
      });
    }
  }
}
