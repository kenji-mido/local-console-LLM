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
import { FormsModule } from '@angular/forms';
import { MatInputModule } from '@angular/material/input';
import { IconTextComponent } from '../icon-text/icon-text.component';
import { FileInputComponent } from './file-input.component';

describe('FileInputComponent', () => {
  let component: FileInputComponent;
  let fixture: ComponentFixture<FileInputComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        FormsModule,
        MatInputModule,
        FileInputComponent,
        IconTextComponent,
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(FileInputComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create the component', () => {
    expect(component).toBeTruthy();
  });

  it('should reset the filename when reset() is called', () => {
    component.filename = 'myfile.txt';
    component.reset();
    expect(component.filename).toBe('Not selected');
  });
  it('should not emit fileSelected when user cancels selection in Electron', async () => {
    (window as any).appBridge = {
      isElectron: true,
      // simulate user cancel
      selectFile: jest.fn().mockResolvedValue({
        path: null,
        basename: null,
        data: null,
      }),
    };

    await component.openFilePicker();

    expect(jest.spyOn(component.fileSelected, 'emit')).not.toHaveBeenCalled();
  });
});
