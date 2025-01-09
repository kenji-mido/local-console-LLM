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

import { ScrollingModule } from '@angular/cdk/scrolling';
import {
  Component,
  Directive,
  ElementRef,
  Input,
  OnChanges,
} from '@angular/core';
import { TableVirtualScrollModule } from 'ng-table-virtual-scroll';
import {
  Classification,
  Detection,
  InferenceItem,
  isClassificationInference,
} from '../inference';
import { NgStyle } from '@angular/common';
import { SegmentsComponent } from '../../option/segments.component';
import { FormsModule } from '@angular/forms';
import { JsonBeautifierComponent } from '../../json/json-beautifier.component';
import { LabelsStored } from '@app/layout/pages/data-hub/data-hub.screen';

@Directive({
  selector: '[appRgbBackground]',
  standalone: true,
})
export class RgbBackgroundDirective implements OnChanges {
  @Input('appRgbBackground') color!: [number, number, number];
  constructor(private el: ElementRef) {}

  ngOnChanges() {
    const [r, g, b] = this.color;
    this.el.nativeElement.style.backgroundColor = `rgb(${r},${g},${b})`;
  }
}

@Component({
  selector: 'app-inference-display',
  standalone: true,
  imports: [
    RgbBackgroundDirective,
    ScrollingModule,
    TableVirtualScrollModule,
    NgStyle,
    SegmentsComponent,
    FormsModule,
    JsonBeautifierComponent,
  ],
  host: { class: 'fullwidth fullheight stack gap-2' },
  styleUrl: './inference-display.component.scss',
  templateUrl: './inference-display.component.html',
})
export class InferenceDisplayComponent {
  isClassificationInference = isClassificationInference;

  protected rawInference?: Classification | Detection;
  protected inferenceItems: InferenceItem[] = [];
  protected displayMode: 'Label' | 'Json' = 'Label';

  @Input() disabled = false;
  @Input() labels: LabelsStored = { labels: [], applied: false };
  @Input() set inference(inf: Classification | Detection | undefined) {
    this.rawInference = inf;
    if (!inf) {
      this.inferenceItems = [];
      return;
    }

    if (isClassificationInference(inf)) {
      inf.perception.classification_list.forEach((item) => {
        if (item.class_id > this.labels.labels.length - 1) {
          item.label = 'Class ' + item.class_id;
        } else {
          item.label = this.labels.labels[item.class_id];
        }
      });

      this.inferenceItems = inf.perception.classification_list;
    } else {
      console.log(inf.perception.object_detection_list);
      inf.perception.object_detection_list.forEach((item) => {
        if (item.class_id > this.labels.labels.length - 1) {
          item.label = 'Class ' + item.class_id;
        } else {
          item.label = this.labels.labels[item.class_id];
        }
      });
      this.inferenceItems = inf.perception.object_detection_list;
      console.log(this.inferenceItems);
    }
  }
}
