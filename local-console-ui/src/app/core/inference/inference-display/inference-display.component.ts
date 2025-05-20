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
import { NgStyle } from '@angular/common';
import {
  Component,
  Directive,
  ElementRef,
  Input,
  OnChanges,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { getColorString, OkColor } from '@app/core/drawing/color';
import { LabelsStored } from '@app/layout/pages/data-hub/data-hub.screen';
import { TableVirtualScrollModule } from 'ng-table-virtual-scroll';
import { InfotipDirective } from '../../feedback/infotip.component';
import { JsonBeautifierComponent } from '../../json/json-beautifier.component';
import { Segment, SegmentsComponent } from '../../option/segments.component';
import {
  InferenceItem,
  InferenceLike,
  isClassificationInference,
  isDetectionInference,
  isErrorInference,
} from '../inference';

@Directive({
  selector: '[appRgbBackground]',
  standalone: true,
})
export class RgbBackgroundDirective implements OnChanges {
  @Input('appRgbBackground') color!: OkColor;
  constructor(private el: ElementRef) {}

  ngOnChanges() {
    this.el.nativeElement.style.backgroundColor = getColorString(this.color);
  }
}

export enum InferenceDisplayMode {
  all,
  rawOnly,
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
    InfotipDirective,
  ],
  host: { class: 'fullwidth fullheight col gap-3' },
  styleUrl: './inference-display.component.scss',
  templateUrl: './inference-display.component.html',
})
export class InferenceDisplayComponent {
  isClassificationInference = isClassificationInference;
  isDetectionInference = isDetectionInference;
  isErrorInference = isErrorInference;

  private __currentMode?: InferenceDisplayMode;

  protected rawInference?: InferenceLike;
  protected inferenceItems: InferenceItem[] = [];
  protected displayMode: 'Label' | 'Json' = 'Label';
  protected displayOptions: Array<Segment | string> = ['Label', 'Json'];

  @Input() disabled = false;
  @Input() error = false;
  @Input() labels: LabelsStored = { labels: [], applied: false };
  @Input() set inference(inf: InferenceLike | undefined) {
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
    } else if (isDetectionInference(inf)) {
      inf.perception.object_detection_list.forEach((item) => {
        if (item.class_id > this.labels.labels.length - 1) {
          item.label = 'Class ' + item.class_id;
        } else {
          item.label = this.labels.labels[item.class_id];
        }
      });
      this.inferenceItems = inf.perception.object_detection_list;
    } else if (isErrorInference(inf)) {
      this.inferenceItems = [
        {
          class_id: 0,
          score: 0,
          label: inf.errorLabel,
          color: { l: 0, c: 0, h: 0 },
        },
      ];
      this.disabled = true;
    } else {
      this.displayMode = 'Json';
    }
  }

  @Input() set mode(mode: InferenceDisplayMode) {
    if (mode !== this.__currentMode) {
      this.__currentMode = mode;
      if (mode === InferenceDisplayMode.rawOnly) {
        this.displayOptions = [
          {
            display: 'Label',
            disabled: true,
            tooltip: 'Labels are not available in User Applications',
          },
          { display: 'Json' },
        ];
        this.displayMode = 'Json';
      } else {
        this.displayOptions = [{ display: 'Label' }, { display: 'Json' }];
      }
    }
  }
}
