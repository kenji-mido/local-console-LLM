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
 * This file incorporates material from a Stack Overflow answer licensed under
 * the Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0) license:
 *
 *     CC BY-SA 4.0
 *     https://creativecommons.org/licenses/by-sa/4.0/
 *
 * Source: https://stackoverflow.com/a/47593316
 * Created by : https://stackoverflow.com/users/815680/bryc
 * The only modification made to the original code is the addition of TypeScript typings.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

function splitmix32(a: number) {
  return function () {
    a |= 0;
    a = (a + 0x9e3779b9) | 0;
    let t = a ^ (a >>> 16);
    t = Math.imul(t, 0x21f0aaad);
    t = t ^ (t >>> 15);
    t = Math.imul(t, 0x735a2d97);
    return ((t = t ^ (t >>> 15)) >>> 0) / 4294967296;
  };
}

export function getGenerator(seed: number = 0.1234) {
  return splitmix32(seed);
}

export function randomString() {
  return Math.random().toString(36).slice(2, 10); // 8 random chars
}
