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
import { Classification } from '../inference';
import {
  InferenceDisplayComponent,
  InferenceDisplayMode,
} from './inference-display.component';

const mockClassification = {
  perception: {
    classification_list: [{ class_id: 0 }, { class_id: 2 }, { class_id: 5 }],
  },
};

const mockDetection = {
  perception: {
    object_detection_list: [{ class_id: 1 }, { class_id: 3 }],
  },
};

describe('InferenceDisplayComponent', () => {
  let component: InferenceDisplayComponent;
  let fixture: ComponentFixture<InferenceDisplayComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [InferenceDisplayComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(InferenceDisplayComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should handle classification inference', () => {
    component.labels = { labels: ['A', 'B', 'C'], applied: true };
    component.inference = mockClassification as Classification;
    expect(component['inferenceItems'].length).toBe(3);
    expect(component['inferenceItems'][0].label).toBe('A');
    expect(component['inferenceItems'][1].label).toBe('C');
    expect(component['inferenceItems'][2].label).toBe('Class 5');
  });

  it('should handle detection inference', () => {
    component.labels = { labels: ['Dog', 'Cat', 'Bird'], applied: true };
    component.inference = mockDetection as any;
    expect(component['inferenceItems'][0].label).toBe('Cat');
    expect(component['inferenceItems'][1].label).toBe('Class 3');
  });

  it('should update display options on mode change', () => {
    component.mode = InferenceDisplayMode.rawOnly;
    expect(component['displayOptions'][0]).toEqual({
      display: 'Label',
      disabled: true,
      tooltip: 'Labels are not available in User Applications',
    });
    expect(component['displayMode']).toBe('Json');
  });
});
