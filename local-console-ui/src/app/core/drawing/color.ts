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

import { getGenerator } from '../common/random.utils';

export const COLOR_STD_CHROMA = 0.25;

export interface OkColor {
  l: number;
  c: number;
  h: number;
}

export function getRandomColorOklch(seed: number): OkColor {
  const prng = getGenerator(seed);
  const h = ((seed * 0.618033988749895 * 1.5 + 0.3 + prng()) * 180) / Math.PI;
  const l = prng() * 0.45 + 0.4;
  return {
    l,
    c: COLOR_STD_CHROMA,
    h,
  };
}

export function getColorString(color: OkColor) {
  return `oklch(${color.l} ${color.c} ${color.h})`;
}

export function getColorLuminance(color: OkColor) {
  return color.l;
}
