/*
 * SPDX-FileCopyrightText: 2023-2024 Sony Semiconductor Solutions Corporation
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * Compile this source into WASM by using Clang from a WASI-SDK installation:
 * $ clang --target=wasm32-wasi dummy_module.c -o classification.wasm
 */
#include <stdio.h>
#include <stdlib.h>

int main() {
    printf("Hello, World\n");
}
