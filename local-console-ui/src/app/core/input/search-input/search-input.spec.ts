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

import { ComponentFixture, TestBed } from '@angular/core/testing';
import {
  FormControl,
  FormGroup,
  FormGroupDirective,
  FormsModule,
  ReactiveFormsModule,
} from '@angular/forms';
import { MatInputModule } from '@angular/material/input';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { SearchInputComponent, SearchInputItem } from './search-input';

describe('SearchInputComponent', () => {
  let fixture: ComponentFixture<SearchInputComponent<SearchInputItem>>;
  let component: SearchInputComponent<SearchInputItem>;
  let formGroupDirective: FormGroupDirective;

  const items: SearchInputItem[] = [
    { value: 'Apple' },
    { value: 'Banana' },
    { value: 'Cherry' },
  ];

  beforeEach(() => {
    const mockFormGroup = new FormGroup({
      mqtt_host: new FormControl(''),
    });
    formGroupDirective = new FormGroupDirective([], []);
    formGroupDirective.form = mockFormGroup;
    TestBed.configureTestingModule({
      imports: [
        ReactiveFormsModule,
        FormsModule,
        MatInputModule,
        NoopAnimationsModule,
        SearchInputComponent,
      ],
      providers: [
        { provide: FormGroupDirective, useValue: formGroupDirective },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(SearchInputComponent);
    component = fixture.componentInstance;
    component.formName = 'mqtt_host';
    component.items.set(items);
    fixture.detectChanges();
  });

  it('should render the component', () => {
    const facade = fixture.debugElement.query(By.css('[data-testid="facade"]'));
    expect(facade).toBeTruthy();
  });

  it('should toggle editing mode on facade click', () => {
    const facade = fixture.debugElement.query(By.css('[data-testid="facade"]'));
    facade.nativeElement.click();
    fixture.detectChanges();

    const input = fixture.debugElement.query(
      By.css('[data-testid="editing-input"]'),
    );
    expect(input).toBeTruthy();
  });

  it('should filter items based on query input', async () => {
    const facade = fixture.debugElement.query(By.css('[data-testid="facade"]'));
    facade.nativeElement.click();
    fixture.detectChanges();

    const input = fixture.debugElement.query(
      By.css('[data-testid="editing-input"]'),
    );
    input.nativeElement.value = 'a';
    input.nativeElement.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    await fixture.whenRenderingDone();

    const filteredItems = fixture.debugElement.queryAll(By.css('.dropdown li'));
    expect(filteredItems.length).toBe(3);
  });

  it('should handle keyboard navigation and select item on Enter', () => {
    const facade = fixture.debugElement.query(By.css('[data-testid="facade"]'));
    facade.nativeElement.click();
    fixture.detectChanges();

    const input = fixture.debugElement.query(
      By.css('[data-testid="editing-input"]'),
    );
    component.handleKeydown(new KeyboardEvent('keydown', { key: 'ArrowDown' }));
    component.handleKeydown(new KeyboardEvent('keydown', { key: 'Enter' }));
    fixture.detectChanges();

    expect(component.selectedItem()?.value).toBe('Apple');
    expect(
      fixture.debugElement.query(By.css('[data-testid="editing-input"] input'))
        .nativeElement.textContent,
    ).toBe('');
  });

  it('should close dropdown on Escape key', () => {
    const facade = fixture.debugElement.query(By.css('[data-testid="facade"]'));
    facade.nativeElement.click(); // Start editing, opening the dropdown
    fixture.detectChanges();

    const input = fixture.debugElement.query(
      By.css('[data-testid="editing-input"]'),
    );
    component.handleKeydown(new KeyboardEvent('keydown', { key: 'Escape' })); // Simulate Escape key press
    fixture.detectChanges();

    const dropdown = fixture.debugElement.query(
      By.css('[data-testid="dropdown"]'),
    );
    expect(dropdown).toBeNull(); // Assert the dropdown is removed
  });

  it('should disable editing if fewer than 2 items', () => {
    component.items.set([items[0]]);
    fixture.detectChanges();

    const facade = fixture.debugElement.query(By.css('[data-testid="facade"]'));
    facade.nativeElement.click();
    fixture.detectChanges();

    const input = fixture.debugElement.query(
      By.css('[data-testid="editing-input"]'),
    );
    expect(input).toBeFalsy();
  });
});
