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

export enum ButtonVariant {
  negative = 'normal-hub-btn', // Just like normal for now
  normal = 'normal-hub-btn',
  weak = 'weak-hub-btn',
}

export interface ActionButton {
  id: string;
  text: string;
  variant: ButtonVariant;
  icon?: string;
}
function actionBuilder(
  id: string,
  text: string,
  variant: ButtonVariant,
  icon?: string,
) {
  return <ActionButton>{
    id,
    text,
    variant,
    icon,
  };
}

export namespace action {
  export function normal(id: string, text: string, icon?: string) {
    return actionBuilder(id, text, ButtonVariant.normal, icon);
  }
  export function weak(id: string, text: string, icon?: string) {
    return actionBuilder(id, text, ButtonVariant.weak, icon);
  }
  export function negative(id: string, text: string, icon?: string) {
    return actionBuilder(id, text, ButtonVariant.negative, icon);
  }
}
