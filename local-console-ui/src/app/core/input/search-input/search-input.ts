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

import { CommonModule } from '@angular/common';
import {
  Component,
  computed,
  ContentChild,
  effect,
  ElementRef,
  Input,
  model,
  signal,
  TemplateRef,
  ViewChild,
} from '@angular/core';
import {
  ControlContainer,
  FormGroupDirective,
  ReactiveFormsModule,
} from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

export interface SearchInputItem {
  value: string; // Used for the real input value
}

@Component({
  selector: 'app-search-input',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatInputModule,
    MatFormFieldModule,
  ],
  viewProviders: [
    {
      provide: ControlContainer,
      useExisting: FormGroupDirective,
    },
  ],
  templateUrl: './search-input.html',
  styleUrls: ['./search-input.scss'],
})
export class SearchInputComponent<T extends SearchInputItem> {
  @ContentChild(TemplateRef) template!: TemplateRef<any>;
  @Input() formName: string = '';
  @ViewChild('inputField') set inputElement(
    input: ElementRef<HTMLInputElement>,
  ) {
    const inputEl = input?.nativeElement;
    if (inputEl && inputEl !== document.activeElement) {
      inputEl.focus();
      inputEl.setSelectionRange(0, inputEl.value.length);
    }
  }
  @ViewChild('dropdown') dropdownElement!: ElementRef<HTMLDivElement>;

  items = model([] as T[]);
  query = signal('');
  filteredItems = signal<T[]>([]);
  selectedItem = signal<T | null>(null);
  showDropdown = signal(false);
  isEditing = signal(false);
  selectedIndex = signal(-1);
  disabled = computed(() => this.items().length < 2);

  constructor(private controlContainer: ControlContainer) {
    effect(() => {
      const index = this.selectedIndex();
      if (index >= 0 && this.dropdownElement) {
        this.dropdownElement.nativeElement.children
          .item(index)
          ?.scrollIntoView({
            behavior: 'smooth',
            block: 'nearest',
            inline: 'nearest',
          });
      }
    });
    effect(
      () => {
        if (this.items().length === 1) {
          this.selectItem(this.items()[0], false);
        }
      },
      { allowSignalWrites: true },
    );
  }

  startEditing() {
    if (this.items().length > 1) {
      this.isEditing.set(true);
      this.filteredItems.set([...this.items()]);
    }
  }

  stopEditing() {
    this.showDropdown.set(false);
    this.isEditing.set(false);
    const selected = this.selectedItem();
    if (selected) {
      this.selectItem(selected);
    }
  }

  onFocus() {
    this.showDropdown.set(true);
  }

  // Update filtered items on query change
  onQueryChange(query: string) {
    this.query.set(query);
    this.filteredItems.set(
      this.items().filter((item) =>
        item.value.toLowerCase().includes(query.toLowerCase()),
      ),
    );
    this.selectedIndex.set(-1);
  }

  // Handle keyboard navigation
  handleKeydown(event: KeyboardEvent) {
    if (event.key === 'ArrowDown') {
      this.selectedIndex.set(
        (this.selectedIndex() + 1) % this.filteredItems().length,
      );
    } else if (event.key === 'ArrowUp') {
      this.selectedIndex.set(
        (this.selectedIndex() - 1 + this.filteredItems().length) %
          this.filteredItems().length,
      );
    } else if (event.key === 'Enter' && this.selectedIndex() !== -1) {
      this.selectItem(this.filteredItems()[this.selectedIndex()]);
    } else if (event.key === 'Escape') {
      this.stopEditing();
    }
  }

  selectItem(item: T, dirty = true) {
    this.selectedItem.set(item);
    this.query.set(item.value);
    const control = this.controlContainer.control?.get(this.formName);
    if (control) {
      control.setValue(item.value);
      if (dirty) {
        control.markAsDirty();
      } else {
        control.markAsPristine();
      }
    }
  }

  handleMouseDown(item: T) {
    this.selectItem(item);
    this.stopEditing();
  }

  reset() {
    if (this.items().length === 1) {
      this.selectItem(this.items()[0], false);
    } else {
      this.selectedItem.set(null);
      this.query.set('');
      this.selectedIndex.set(0);
      const control = this.controlContainer.control?.get(this.formName);
      control?.setValue('');
      control?.markAsPristine();
    }
  }
}
