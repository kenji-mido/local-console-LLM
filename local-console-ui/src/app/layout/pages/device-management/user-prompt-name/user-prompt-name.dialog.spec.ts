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

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { UserPromptNameDialog } from './user-prompt-name.dialog';
import { UserPromptDialogData } from '../../../dialogs/user-prompt/user-prompt.dialog';
import { DialogRef, DIALOG_DATA } from '@angular/cdk/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

describe('UserPromptDialog', () => {
  let component: UserPromptNameDialog;
  let fixture: ComponentFixture<UserPromptNameDialog>;
  let dialogRefSpy: jest.Mocked<DialogRef<UserPromptNameDialog>>;
  let dialogData: UserPromptDialogData = {
    title: 'Test Title',
    message: 'Test message',
    type: 'info',
    actionButtons: [{ text: 'Test', id: 'test', variant: 'primary' }],
    closeButtonText: 'Close',
  };
  beforeEach(async () => {
    dialogRefSpy = { close: jest.fn() } as any;

    await TestBed.configureTestingModule({
      imports: [UserPromptNameDialog, NoopAnimationsModule], // Import standalone component
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
    expect(component.device_name).toEqual(null);
  });

  it('should return null ngOnDestroy', () => {
    component.ngOnDestroy();
    expect(dialogRefSpy.close).toHaveBeenCalledWith(null);
  });

  it('should return name ngOnDestroy if onApply was called', () => {
    component.inputs.value.device_name = 'device_name';
    component.onApply();
    component.ngOnDestroy();
    expect(dialogRefSpy.close).toHaveBeenCalledWith('device_name');
  });
});
