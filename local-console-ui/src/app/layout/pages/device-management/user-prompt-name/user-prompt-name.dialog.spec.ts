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
import { ButtonVariant } from '@app/layout/dialogs/user-prompt/action';
import {
  UserPromptNameDialog,
  UserPromptNameDialogData,
} from './user-prompt-name.dialog';

describe('UserPromptNameDialog', () => {
  let component: UserPromptNameDialog;
  let fixture: ComponentFixture<UserPromptNameDialog>;
  let dialogRefSpy: jest.Mocked<DialogRef<UserPromptNameDialog>>;
  let dialogData: UserPromptNameDialogData = {
    title: 'Test Title',
    message: 'Test message',
    type: 'info',
    actionButtons: [
      { text: 'Test', id: 'test', variant: ButtonVariant.normal },
    ],
    closeButtonText: 'Close',
    showCancelButton: true,
    deviceName: 'Device1',
  };

  beforeEach(async () => {
    dialogRefSpy = { close: jest.fn() } as any;

    await TestBed.configureTestingModule({
      imports: [UserPromptNameDialog, NoopAnimationsModule],
      providers: [
        { provide: DialogRef, useValue: dialogRefSpy },
        { provide: DIALOG_DATA, useValue: dialogData },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UserPromptNameDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize with provided data', () => {
    expect(component.deviceName).toEqual('Device1');
  });

  it('should not return name on ngOnDestroy if onApply was not called', () => {
    component.ngOnDestroy();
    expect(dialogRefSpy.close).not.toHaveBeenCalled();
  });

  it('should return name ngOnDestroy if onApply was called', () => {
    component.inputs.value.deviceName = 'mynewname';
    component.onApply();
    component.ngOnDestroy();
    expect(dialogRefSpy.close).toHaveBeenCalledWith('mynewname');
  });
});
