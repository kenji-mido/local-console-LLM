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

import { Component, model, viewChild } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { signalTracker } from './signal-tracker';

describe('TrackedSignal', () => {
  let fixture: ComponentFixture<SignalTestComponent>;
  let component: SignalTestComponent;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [SignalTestComponent],
    });

    fixture = TestBed.createComponent(SignalTestComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  describe('Functional Tests', () => {
    it('should initialize with the correct value', () => {
      expect(component.signal()).toBe(0);
      expect(component.signalTracker.touched()).toBe(false);
    });

    it('should mark as touched when set', () => {
      component.signal.set(42);
      expect(component.signal()).toBe(42);
      fixture.detectChanges();
      expect(component.signalTracker.touched()).toBe(true);
    });

    it('should reset', () => {
      component.signal.set(10);
      fixture.detectChanges();
      expect(component.signalTracker.touched()).toBe(true);

      component.signalTracker.reset();
      expect(component.signalTracker.touched()).toBe(false);
    });
  });
});

describe('TrackedSignal - Dual Binding and Effect Tests', () => {
  let fixture: ComponentFixture<ParentComponent>;
  let parentComponent: ParentComponent;
  let childComponent: ChildComponent;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [ParentComponent, ChildComponent],
    });

    fixture = TestBed.createComponent(ParentComponent);
    parentComponent = fixture.componentInstance;
    fixture.detectChanges();
    childComponent = parentComponent.child();
  });

  it('should initialize parent and child values correctly', () => {
    expect(parentComponent.value()).toBe(0);
    expect(childComponent.model()).toBe(0);
  });

  it('should reflect changes made in the child', () => {
    childComponent.model.set(100);
    fixture.detectChanges();

    expect(parentComponent.value()).toBe(100);
  });

  it('should reflect changes made in the parent', () => {
    parentComponent.value.set(5);
    fixture.detectChanges();

    expect(childComponent.model()).toBe(5);
  });

  it('should maintain the touched state when the value is updated', () => {
    expect(childComponent.modelTracker.touched()).toBe(false);

    parentComponent.value.set(50);
    fixture.detectChanges();

    expect(childComponent.modelTracker.touched()).toBe(true);
  });

  it('should reset the touched state', async () => {
    parentComponent.value.set(50);
    fixture.detectChanges();
    expect(childComponent.modelTracker.touched()).toBe(true);

    childComponent.modelTracker.reset();

    expect(childComponent.modelTracker.touched()).toBe(false);
    expect(childComponent.model()).toBe(50);
  });
});

// -------------------- TEST COMPONENTS --------------------

@Component({
  selector: 'app-signal-test',
  template: `
    <p>Value: {{ signal() }}</p>
    <p>Touched: {{ signalTracker.touched() }}</p>
    <button (click)="signal.set(signal() + 1)">Increment</button>
    <button (click)="signalTracker.reset()">Reset</button>
  `,
})
export class SignalTestComponent {
  signal = model(0);
  signalTracker = signalTracker<number>(this.signal);
}

@Component({
  selector: 'app-child',
  standalone: true,
  template: `<p></p> `,
})
export class ChildComponent {
  //   model = model(0);
  model = model(0);
  modelTracker = signalTracker<number>(this.model);
}

@Component({
  selector: 'app-parent',
  standalone: true,
  imports: [ChildComponent],
  template: ` <app-child [(model)]="value"></app-child> `,
})
export class ParentComponent {
  value = model(0);
  child = viewChild.required(ChildComponent);
}
