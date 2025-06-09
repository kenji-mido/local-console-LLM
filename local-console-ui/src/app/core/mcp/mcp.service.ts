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

import { Injectable, signal } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

export interface McpConfig {
  serverUrl: string;
  apiKey?: string;
  timeout?: number;
}

export interface McpTool {
  name: string;
  description: string;
  inputSchema?: any;
}

export interface McpResource {
  uri: string;
  name: string;
  description?: string;
  mimeType?: string;
}

@Injectable({
  providedIn: 'root'
})
export class McpService {
  private config = signal<McpConfig | null>(null);
  private connectionStatus = new BehaviorSubject<boolean>(false);
  private ws: WebSocket | null = null;
  private messageHandlers = new Map<string, (data: any) => void>();
  private requestId = 0;

  connectionStatus$ = this.connectionStatus.asObservable();

  constructor() {
    // Load config from localStorage if exists
    const savedConfig = localStorage.getItem('mcp-config');
    if (savedConfig) {
      try {
        const config = JSON.parse(savedConfig);
        this.connect(config);
      } catch (e) {
        console.error('Failed to parse saved MCP config:', e);
      }
    }
  }

  async connect(config: McpConfig): Promise<boolean> {
    this.config.set(config);
    // TODO: Consider secure storage for sensitive configuration
    localStorage.setItem('mcp-config', JSON.stringify(config));

    if (this.ws) {
      this.ws.close();
    }

    return new Promise((resolve) => {
      try {
        this.ws = new WebSocket(config.serverUrl);

        this.ws.onopen = () => {
          console.log('MCP WebSocket connected');
          this.connectionStatus.next(true);
          this.initialize();
          resolve(true);
        };

        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (e) {
            console.error('Failed to parse MCP message:', e);
          }
        };

        this.ws.onerror = (error) => {
          console.error('MCP WebSocket error:', error);
          this.connectionStatus.next(false);
          resolve(false);
        };

        this.ws.onclose = () => {
          console.log('MCP WebSocket closed');
          this.connectionStatus.next(false);
        };

      } catch (error) {
        console.error('Failed to connect to MCP server:', error);
        resolve(false);
      }
    });
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.connectionStatus.next(false);
  }

  async queryData(query: string): Promise<any> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('MCP not connected');
    }

    const lowerQuery = query.toLowerCase();

    // If user asks for tools or capabilities, return available tools
    if (lowerQuery.includes('tools') || lowerQuery.includes('available') || lowerQuery.includes('capabilities')) {
      return {
        availableTools: await this.listTools(),
        message: 'Here are the available MCP tools. Use specific tool names to execute them.'
      };
    }

    // For any other query, return available tools for user guidance
    // The user should specify which tool to use
    return {
      message: 'Please specify which tool you want to use. Ask "what tools are available?" to see all options.',
      availableTools: await this.listTools()
    };
  }

  async callTool(toolName: string, toolArgs: any = {}): Promise<any> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('MCP not connected');
    }

    const id = this.generateRequestId();
    const request = {
      jsonrpc: '2.0',
      id,
      method: 'tools/call',
      params: {
        name: toolName,
        arguments: toolArgs
      }
    };

    return this.sendRequest(request);
  }

  async listTools(): Promise<McpTool[]> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('MCP not connected');
    }

    const id = this.generateRequestId();
    const request = {
      jsonrpc: '2.0',
      id,
      method: 'tools/list',
      params: {}
    };

    const response = await this.sendRequest(request);
    return response.tools || [];
  }

  async listResources(): Promise<McpResource[]> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('MCP not connected');
    }

    const id = this.generateRequestId();
    const request = {
      jsonrpc: '2.0',
      id,
      method: 'resources/list',
      params: {}
    };

    const response = await this.sendRequest(request);
    return response.resources || [];
  }

  getConfig(): McpConfig | null {
    return this.config();
  }

  async getToolCapabilities(): Promise<{tools: McpTool[], resources: McpResource[]}> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('MCP not connected');
    }

    const [tools, resources] = await Promise.all([
      this.listTools(),
      this.listResources()
    ]);

    return { tools, resources };
  }

  private initialize() {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

    const initRequest = {
      jsonrpc: '2.0',
      id: this.generateRequestId(),
      method: 'initialize',
      params: {
        protocolVersion: '2024-11-05',
        capabilities: {
          roots: { listChanged: true },
          sampling: {}
        },
        clientInfo: {
          name: 'LocalConsole',
          version: '1.0.0'
        }
      }
    };

    this.sendRequest(initRequest).catch(console.error);
  }

  private sendRequest(request: any): Promise<any> {
    return new Promise((resolve, reject) => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        reject(new Error('WebSocket not connected'));
        return;
      }

      const timeout = setTimeout(() => {
        this.messageHandlers.delete(request.id);
        reject(new Error('Request timeout'));
      }, this.config()?.timeout || 30000);

      this.messageHandlers.set(request.id, (response) => {
        clearTimeout(timeout);
        this.messageHandlers.delete(request.id);

        if (response.error) {
          reject(response.error);
        } else {
          resolve(response.result);
        }
      });

      this.ws.send(JSON.stringify(request));
    });
  }

  private handleMessage(message: any) {
    if (message.id && this.messageHandlers.has(message.id)) {
      const handler = this.messageHandlers.get(message.id);
      if (handler) {
        handler(message);
      }
    } else if (message.method) {
      // Handle notifications
      console.log('MCP notification:', message);
    }
  }

  private generateRequestId(): string {
    return `req_${++this.requestId}`;
  }
}