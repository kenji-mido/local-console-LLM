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

import { Component } from '@angular/core';
import { TestBed, ComponentFixture } from '@angular/core/testing';
import { DialogRef, DialogModule } from '@angular/cdk/dialog';
import { By } from '@angular/platform-browser';
import { DialogCloseDirective } from './dialog.close.directive';

// Mock component to test directive
@Component({
  template: `<button appDialogClose>Close</button>`,
  standalone: true,
  imports: [DialogCloseDirective],
})
class TestButtonComponent {}

describe('DialogCloseDirective', () => {
  let component: TestButtonComponent;
  let fixture: ComponentFixture<TestButtonComponent>;
  let dialogRefSpyObj = { close: jest.fn() };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [{ provide: DialogRef, useValue: dialogRefSpyObj }],
      imports: [DialogModule, TestButtonComponent],
    });

    fixture = TestBed.createComponent(TestButtonComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create an instance of the test component', () => {
    expect(component).toBeTruthy();
  });

  it('should close the dialog when clicked', () => {
    const button = fixture.debugElement.query(By.css('button'));
    button.triggerEventHandler('click', null);
    expect(dialogRefSpyObj.close).toHaveBeenCalled();
  });

  it('should not throw an error if dialogRef is not injected', () => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      imports: [TestButtonComponent],
    });
    fixture = TestBed.createComponent(TestButtonComponent);
    expect(() => fixture.detectChanges()).not.toThrow();
  });

  it('should log a warning to the console if dialogRef is not provided', () => {
    const consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      imports: [TestButtonComponent],
    });
    fixture = TestBed.createComponent(TestButtonComponent);
    fixture.detectChanges();
    expect(consoleWarnSpy).toHaveBeenCalledWith(
      "Hey, you're using the appDialogClose directive outside a CDK Dialog. This won't work!",
    );
    consoleWarnSpy.mockRestore();
  });
});
