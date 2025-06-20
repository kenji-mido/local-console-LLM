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

import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { action } from './action';
import { UserPromptDialog, UserPromptDialogData } from './user-prompt.dialog';

describe('UserPromptDialog', () => {
  let component: UserPromptDialog;
  let fixture: ComponentFixture<UserPromptDialog>;
  let dialogRefSpy: jest.Mocked<DialogRef<UserPromptDialog>>;
  let dialogData: UserPromptDialogData = {
    title: 'Test Title',
    message: 'Test message',
    type: 'info',
    actionButtons: [action.normal('Test', 'test')],
    closeButtonText: 'Close',
    showCancelButton: true,
  };

  beforeEach(async () => {
    dialogRefSpy = { close: jest.fn() } as any;

    await TestBed.configureTestingModule({
      imports: [UserPromptDialog, NoopAnimationsModule], // Import standalone component
      providers: [
        { provide: DialogRef, useValue: dialogRefSpy },
        { provide: DIALOG_DATA, useValue: dialogData },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UserPromptDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize with provided data', () => {
    expect(component.data).toEqual(dialogData);
  });

  it('should clean up on ngOnDestroy', () => {
    component.ngOnDestroy();
    expect(component.data.actionButtons).toBeUndefined();
  });
});
