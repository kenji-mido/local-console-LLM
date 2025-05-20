# Copyright 2024 Sony Semiconductor Solutions Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
"""
The AoT format has a fixed header structure, as implemented at:
https://github.com/bytecodealliance/wasm-micro-runtime/blob/f2e3348305d16cde5a45f4dda585a0caf01a0fb4/core/iwasm/compilation/aot_emit_aot_file.c#L1693
"""

AOT_HEADER = [0x00, ord("a"), ord("o"), ord("t")]
