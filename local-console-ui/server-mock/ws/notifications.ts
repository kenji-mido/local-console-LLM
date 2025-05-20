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

import { Express } from 'express';
import { Server } from 'http';
import { WebSocketServer } from 'ws';

export function registerNotificationsWebSocketController(
  server: Server,
  app: Express,
) {
  const wss = new WebSocketServer({ server, path: '/ws/' });

  // WS
  wss.on('connection', (ws, request) => {
    console.log(`Client connected to ${request.headers.host}`);
    ws.on('close', () => console.log(`Client disconnected`));
  });

  app.post('/notify', (req, res) => {
    const payload = req.body;
    wss.clients.forEach((client) => {
      if (client.readyState === 1) {
        client.send(JSON.stringify(payload));
      }
    });
    res.json({ success: true, sent: payload });
  });
}
