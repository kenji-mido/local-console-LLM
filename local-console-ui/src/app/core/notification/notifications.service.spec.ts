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

import { TestBed } from '@angular/core/testing';
import { waitForExpect } from '@test/utils';
import { firstValueFrom } from 'rxjs';
import {
  NotificationKind,
  NotificationsService,
} from './notifications.service';

describe('WebSocketService', () => {
  let service: NotificationsService;
  let mockWebSocket: WebSocket;

  beforeEach(() => {
    mockWebSocket = {
      send: jest.fn(),
      close: jest.fn(),
      readyState: WebSocket.CLOSED,
    } as unknown as WebSocket;

    global.WebSocket = jest.fn(() => mockWebSocket as WebSocket) as any;
    TestBed.configureTestingModule({ providers: [NotificationsService] });
    service = TestBed.inject(NotificationsService);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('should create the WebSocket connection on init', () => {
    expect(global.WebSocket).toHaveBeenCalledWith(
      expect.stringMatching(/^ws:/),
    );
  });

  it('should reconnect on unexpected close', async () => {
    mockWebSocket.onclose!({ wasClean: false } as CloseEvent);
    await waitForExpect(() => {
      expect(global.WebSocket).toHaveBeenCalledTimes(2);
    });
  });

  it('should not reconnect on clean close', () => {
    mockWebSocket.onclose!({ wasClean: true } as CloseEvent);
    expect(global.WebSocket).toHaveBeenCalledTimes(1);
  });

  it('should emit received messages to correct subscribers', async () => {
    const testMessage = { kind: NotificationKind.ERROR, data: 'testData' };
    const obs = service.on<string>(NotificationKind.ERROR);

    const expected = firstValueFrom(obs);

    mockWebSocket.onmessage!({
      data: JSON.stringify(testMessage),
    } as MessageEvent);

    await expect(expected).resolves.toBe('testData');
  });

  it('should clean up WebSocket on destroy', () => {
    service.ngOnDestroy();
    expect(mockWebSocket.close).toHaveBeenCalled();
  });

  it('should correctly filter messages for multiple subscribers on different channels', async () => {
    const obs1 = service.on<string>(NotificationKind.ERROR);
    const obs2 = service.on<string>(NotificationKind.DEVICE_NO_QUOTA);
    const expected1 = firstValueFrom(obs1);
    const expected2 = firstValueFrom(obs2);

    mockWebSocket.onmessage!({
      data: JSON.stringify({ kind: NotificationKind.ERROR, data: 'data1' }),
    } as MessageEvent);
    mockWebSocket.onmessage!({
      data: JSON.stringify({
        kind: NotificationKind.DEVICE_NO_QUOTA,
        data: 'data2',
      }),
    } as MessageEvent);

    await expect(expected1).resolves.toBe('data1');
    await expect(expected2).resolves.toBe('data2');
  });
});
