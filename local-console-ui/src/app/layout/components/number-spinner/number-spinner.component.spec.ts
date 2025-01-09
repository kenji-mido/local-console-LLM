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
import { NumberSpinnerComponent } from './number-spinner.component';
import { FormsModule } from '@angular/forms';

describe('NumberSpinnerComponent', () => {
  let component: NumberSpinnerComponent;
  let fixture: ComponentFixture<NumberSpinnerComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NumberSpinnerComponent, FormsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(NumberSpinnerComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    jest.clearAllTimers();
    jest.useFakeTimers();
  });

  it('should create the component', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize with default values', () => {
    expect(component.label).toBe('');
    expect(component.data).toBe(10);
    expect(component.default).toBe(10);
    expect(component.min).toBe(1);
    expect(component.max).toBe(20);
    expect(component.step).toBe(1);
    expect(component.editableDisabled).toBe(true);
    expect(component.minusPlusDisabled).toBe(true);
  });

  it('should increment data when plus is clicked', () => {
    const emitSpy = jest.spyOn(component.DataChange, 'emit');
    component.data = 10;
    component.step = 1;
    component.plus();
    expect(component.data).toBe(11);
    expect(emitSpy).toHaveBeenCalledWith(11);
  });

  it('should decrement data when minus is clicked', () => {
    const emitSpy = jest.spyOn(component.DataChange, 'emit');
    component.data = 10;
    component.step = 1;
    component.minus();
    expect(component.data).toBe(9);
    expect(emitSpy).toHaveBeenCalledWith(9);
  });

  it('should not exceed max value', () => {
    component.data = component.max;
    component.plus();
    expect(component.data).toBe(component.max);
  });

  it('should not go below min value', () => {
    component.data = component.min;
    component.minus();
    expect(component.data).toBe(component.min);
  });

  it('should reset to max after invalid input', () => {
    component.data = 13;
    component.onInputChange(25);
    jest.advanceTimersByTime(component.INVALID_INTERVAL);
    expect(component.data).toBe(20);
    component.onInputChange(100);
    jest.advanceTimersByTime(component.INVALID_INTERVAL);
    expect(component.data).toBe(20);
    component.onInputChange(19);
    jest.advanceTimersByTime(component.INVALID_INTERVAL);
    expect(component.data).toBe(19);
  });

  it('should reset to min after invalid input', () => {
    component.data = 13;
    component.onInputChange(0);
    jest.advanceTimersByTime(component.INVALID_INTERVAL);
    expect(component.data).toBe(1);
    component.onInputChange(-1);
    jest.advanceTimersByTime(component.INVALID_INTERVAL);
    expect(component.data).toBe(1);
    component.onInputChange(3);
    jest.advanceTimersByTime(component.INVALID_INTERVAL);
    expect(component.data).toBe(3);
  });

  it('should reset to default when invalid argument', () => {
    component.data = 13;
    component.onInputChange(-1);
    jest.advanceTimersByTime(component.INVALID_INTERVAL);
    expect(component.data).toBe(1);
    component.onInputChange(null);
    jest.advanceTimersByTime(component.INVALID_INTERVAL);
    expect(component.data).toBe(10);
  });
});
