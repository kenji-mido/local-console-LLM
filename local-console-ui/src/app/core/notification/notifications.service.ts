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

import { Injectable } from '@angular/core';
import { Observable, Subject, filter, map } from 'rxjs';
import { EnvService } from '../common/environment.service';

export const RETRY_TIMEOUT = 1000;

export enum NotificationKind {
  ERROR = 'error',
  DEVICE_NO_QUOTA = 'storage-limit-hit',
}

interface WebSocketMessage<T = any> {
  kind: string;
  data: T;
}

@Injectable({ providedIn: 'root' })
export class NotificationsService {
  private socket: WebSocket | null = null;
  private messageSubject = new Subject<WebSocketMessage>();

  private readonly url: string;
  private isDestroyed = false;

  constructor(private envService: EnvService) {
    this.url = envService.getApiUrl().replace(/^http/, 'ws') + '/ws/';
    this.connect();
  }

  private connect(): void {
    if (this.isDestroyed) return;

    this.socket = new WebSocket(this.url);

    this.socket.onopen = () => {
      console.log('WebSocket connected');
    };

    this.socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        if (
          typeof parsed === 'object' &&
          'kind' in parsed &&
          'data' in parsed
        ) {
          this.messageSubject.next(parsed);
        } else {
          console.warn('Received non-standard message:', event.data);
        }
      } catch {
        console.warn('Received non-JSON message:', event.data);
        this.messageSubject.next({ kind: 'RAW_STRING', data: event.data });
      }
    };

    this.socket.onclose = (event) => {
      if (!event.wasClean) {
        console.warn('WebSocket disconnected unexpectedly, retrying...');
        this.reconnect();
      }
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.reconnect();
    };
  }

  private reconnect(): void {
    if (this.isDestroyed) return;

    setTimeout(() => {
      if (!this.socket || this.socket.readyState === WebSocket.CLOSED) {
        this.connect();
      }
    }, RETRY_TIMEOUT);
  }

  ngOnDestroy(): void {
    this.isDestroyed = true;
    if (this.socket) {
      this.socket.onclose = null;
      this.socket.onerror = null;
      this.socket.onmessage = null;
      this.socket.close();
    }
  }

  on<T = string>(commandName: NotificationKind): Observable<T> {
    return this.messageSubject.asObservable().pipe(
      filter((msg) => msg.kind === commandName),
      map((msg) => msg.data as T),
    );
  }
}
