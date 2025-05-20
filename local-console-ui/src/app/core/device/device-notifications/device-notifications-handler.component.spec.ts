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

import { NO_ERRORS_SCHEMA } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { InferenceResultsService } from '@app/core/inference/inferenceresults.service';
import { NotificationsService } from '@app/core/notification/notifications.service';
import { DialogService } from '@app/layout/dialogs/dialog.service';
import { of } from 'rxjs';
import { DeviceNotificationsHandlerComponent } from './device-notifications-handler.component';

describe('DeviceNotificationsHandlerComponent', () => {
  let component: DeviceNotificationsHandlerComponent;
  let fixture: ComponentFixture<DeviceNotificationsHandlerComponent>;
  let mockNotificationsService: Partial<NotificationsService>;
  let mockDialogService: Partial<DialogService>;
  let mockRouter: Partial<Router>;
  let mockInferencesService: Partial<InferenceResultsService>;

  beforeEach(async () => {
    mockNotificationsService = {
      on: jest.fn(() => of<any>({ device_id: 'test-device' })),
    };

    mockDialogService = {
      prompt: jest.fn(() => Promise.resolve<any>({ id: 'goto' })),
    };

    mockRouter = {
      navigate: jest.fn(),
    };

    mockInferencesService = {
      teardown: jest.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [DeviceNotificationsHandlerComponent],
      providers: [
        { provide: NotificationsService, useValue: mockNotificationsService },
        { provide: DialogService, useValue: mockDialogService },
        { provide: Router, useValue: mockRouter },
        { provide: InferenceResultsService, useValue: mockInferencesService },
      ],
      schemas: [NO_ERRORS_SCHEMA],
    }).compileComponents();

    fixture = TestBed.createComponent(DeviceNotificationsHandlerComponent);
    component = fixture.componentInstance;
  });

  it('should stop inferences and show prompt on quota notification', async () => {
    await fixture.whenStable();
    expect(mockInferencesService.teardown).toHaveBeenCalledWith('test-device');
    expect(mockDialogService.prompt).toHaveBeenCalled();
    expect(mockRouter.navigate).toHaveBeenCalledWith(
      ['/data-hub'],
      expect.any(Object),
    );
  });
});
