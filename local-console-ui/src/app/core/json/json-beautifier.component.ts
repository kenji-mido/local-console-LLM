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

import { CommonModule } from '@angular/common';
import {
  Component,
  Input,
  NgModule,
  Pipe,
  PipeTransform,
  ViewEncapsulation,
} from '@angular/core';

@Pipe({
  standalone: true,
  name: 'split',
})
export class StringSplitterPipe implements PipeTransform {
  transform(value: string, splitter: string = '\n') {
    return value.split(splitter);
  }
}

@Pipe({
  standalone: true,
  name: 'colorizeJson',
  pure: false,
})
export class JsonColorizerPipe implements PipeTransform {
  transform(json: string) {
    json = json
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    return json.replace(
      /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
      function (match) {
        var cls = 'number';
        if (/^"/.test(match)) {
          if (/:$/.test(match)) {
            cls = 'key';
          } else {
            cls = 'string';
          }
        } else if (/true|false/.test(match)) {
          cls = 'boolean';
        } else if (/null/.test(match)) {
          cls = 'null';
        }
        return '<span class="' + cls + '">' + match + '</span>';
      },
    );
  }
}

@NgModule({
  imports: [StringSplitterPipe, JsonColorizerPipe],
  exports: [StringSplitterPipe, JsonColorizerPipe],
})
export class JsonTransformersModule {}

@Component({
  selector: 'app-json',
  standalone: true,
  imports: [CommonModule, JsonTransformersModule],
  encapsulation: ViewEncapsulation.ShadowDom,
  template: `
    <pre>
    @for (line of object | json | split; track $index; let i = $index)  {
      <span class="row">
        <span class="line-number">{{i}}</span>
        <span class="content" [innerHtml]="line | colorizeJson"></span>
      </span>
    }
    </pre>
  `,
  styles: `
    :host {
      height: 100%;
      overflow: auto;
      width: 100%;
    }
    pre {
      font-family: monospace !important;
      font-size: 16px;
      font-weight: 500;
      margin: 0;
      padding: 0;
      width: 100%;
      display: flex;
      flex-direction: column;
      gap: 0;
      box-sizing: border-box;
    }
    .row {
      display: flex;
      width: 100%;
      gap: var(--standard-spacing);
    }
    .line-number {
      color: #4d4d4d;
      padding: calc(var(--standard-spacing) / 2) var(--standard-spacing);
      flex: 34px 0 0;
      background-color: var(--color-edgeaipf-gray);
    }
    .number {
      color: red;
    }
    .string {
      color: #078a1a;
    }
    .boolean {
      color: cyan;
    }
  `,
})
export class JsonBeautifierComponent {
  @Input() object: any;
}
