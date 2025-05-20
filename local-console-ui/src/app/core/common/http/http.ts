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

import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { lastValueFrom, Observable } from 'rxjs';
import { HttpErrorHandler } from './error-handler.service';

@Injectable({
  providedIn: 'root',
})
export class HttpApiClient {
  constructor(
    private http: HttpClient,
    private handler: HttpErrorHandler,
  ) {}

  async get<T = any>(
    path: string,
    queryParams?:
      | HttpParams
      | {
          [param: string]:
            | string
            | number
            | boolean
            | ReadonlyArray<string | number | boolean>;
        },
    showErrorAlert = true,
  ): Promise<T> {
    return this.mapToHandledPromise(
      this.http.get<T>(path, {
        params: queryParams,
      }),
      showErrorAlert,
    );
  }

  /*
  get<ArrayBuffer> does not impose a response format. I'm getting the error:

  SyntaxError: Unexpected token '�', "����JFIF"... is not valid JSON
  at JSON.parse (<anonymous>)
  at XMLHttpRequest.onLoad (http://localhost:4200/@fs/home/tonibc/repos/midokura/local-console/local-console-ui/.angular/cache/18.2.10/local-console-ui/vite/deps/chunk-7MTMC5FO.js?v=d0322418:1648:41)
  at _ZoneDelegate.invokeTask (http://localhost:4200/polyfills.js:327:171)
  at http://localhost:4200/@fs/home/tonibc/repos/midokura/local-console/local-console-ui/.angular/cache/18.2.10/local-console-ui/vite/deps/chunk-VU73NTKM.js?v=d0322418:5626:49
  at AsyncStackTaggingZoneSpec.onInvokeTask (http://localhost:4200/@fs/home/tonibc/repos/midokura/local-console/local-console-ui/.angular/cache/18.2.10/local-console-ui/vite/deps/chunk-VU73NTKM.js?v=d0322418:5626:30)
  at _ZoneDelegate.invokeTask (http://localhost:4200/polyfills.js:327:54)
  at Object.onInvokeTask (http://localhost:4200/@fs/home/tonibc/repos/midokura/local-console/local-console-ui/.angular/cache/18.2.10/local-console-ui/vite/deps/chunk-VU73NTKM.js?v=d0322418:5816:25)
  at _ZoneDelegate.invokeTask (http://localhost:4200/polyfills.js:327:54)
  at ZoneImpl.runTask (http://localhost:4200/polyfills.js:135:37)
  at ZoneTask.invokeTask [as invoke] (http://localhost:4200/polyfills.js:398:26)

  I have created this function as a temporal solution
*/
  async getblob<T = any>(
    path: string,
    queryParams?: HttpParams,
    showErrorAlert = true,
  ): Promise<T> {
    return this.mapToHandledPromise(
      this.http.get(path, {
        params: queryParams,
        responseType: 'arraybuffer',
      }),
      showErrorAlert,
    );
  }

  async post<T = any>(
    path: string,
    payload: any,
    showErrorAlert = true,
  ): Promise<T> {
    return this.mapToHandledPromise(
      this.http.post<T>(path, payload),
      showErrorAlert,
    );
  }

  async patch<T = any>(path: string, payload: any): Promise<T> {
    return this.mapToHandledPromise(this.http.patch<T>(path, payload));
  }

  async put<T = any>(path: string, payload: any): Promise<T> {
    return this.mapToHandledPromise(this.http.put<T>(path, payload));
  }

  async delete<T = any>(
    path: string,
    options?: { headers?: HttpHeaders; body: string },
  ): Promise<T> {
    return this.mapToHandledPromise(this.http.delete<T>(path, options));
  }

  private mapToHandledPromise<T>(obs: Observable<T>, showErrorAlert = true) {
    return this.handler.handlePromise(lastValueFrom(obs), showErrorAlert);
  }
}
