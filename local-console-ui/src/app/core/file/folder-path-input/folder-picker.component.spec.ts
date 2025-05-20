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
import { IconTextComponent } from '../icon-text/icon-text.component';
import { FolderPickerComponent } from './folder-picker.component';

describe('FolderPickerComponent', () => {
  let component: FolderPickerComponent;
  let fixture: ComponentFixture<FolderPickerComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [FolderPickerComponent, IconTextComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(FolderPickerComponent);
    component = fixture.componentInstance;
    component.reset();
    fixture.detectChanges();
  });

  it('should create the FolderPickerComponent', () => {
    expect(component).toBeTruthy();
  });

  it('should reset the folderPath when reset() is called', () => {
    component.folderPath = '/tmp/path';
    component.reset();
    expect(component.folderPath).toBe('Not selected');
  });

  it('should emit folderSelected when a folder is selected in Electron', async () => {
    const testPath = '/test/path';
    const payload = { path: testPath };
    const spy = jest.spyOn(component.folderSelected, 'emit');

    (window as any).appBridge = {
      isElectron: true,
      selectFolder: jest.fn().mockResolvedValue(payload),
    };

    await component.openFolderPicker();

    expect(component.folderPath).toBe(testPath);
    expect(spy).toHaveBeenCalledWith(payload);
  });

  it('should emit folderSelected when a folder is selected in browser', async () => {
    const testFolderName = 'testFolder';
    const payload = { path: testFolderName };
    const spy = jest.spyOn(component.folderSelected, 'emit');

    (window as any).appBridge = undefined;
    (window as any).showDirectoryPicker = jest.fn().mockResolvedValue({
      name: testFolderName,
    });

    await component.openFolderPicker();

    expect(component.folderPath).toBe(testFolderName);
    expect(spy).toHaveBeenCalledWith(payload);
  });

  it('should handle error when folder selection fails in browser', async () => {
    (window as any).appBridge = undefined;
    (window as any).showDirectoryPicker = jest
      .fn()
      .mockRejectedValue(new Error('Folder selection error'));

    component.folderPath = 'Initial Path';
    const spy = jest.spyOn(component.folderSelected, 'emit');

    await component.openFolderPicker();

    expect(component.folderPath).toBe('Initial Path');
    expect(spy).not.toHaveBeenCalled();
  });

  it('should not update folderPath or emit folderSelected when user cancels in Electron', async () => {
    const spy = jest.spyOn(component.folderSelected, 'emit');
    component.folderPath = 'Initial Path';

    (window as any).appBridge = {
      isElectron: true,
      selectFolder: jest.fn().mockResolvedValue({ path: null }),
    };

    await component.openFolderPicker();

    expect(component.folderPath).toBe('Initial Path');
    expect(spy).not.toHaveBeenCalled();
  });

  it('should handle cancellation when user cancels folder selection in browser', async () => {
    (window as any).appBridge = undefined;

    component.folderPath = 'Initial Path';
    const spy = jest.spyOn(component.folderSelected, 'emit');

    await component.openFolderPicker();

    expect(component.folderPath).toBe('Initial Path');
    expect(spy).not.toHaveBeenCalled();
  });
});
