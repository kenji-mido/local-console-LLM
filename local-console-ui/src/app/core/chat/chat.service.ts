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

import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

export interface ChatConfig {
  provider: string;
  apiEndpoint: string;
  apiKey: string;
  model?: string;
  temperature?: number;
  maxTokens?: number;
}

export interface ChatResponse {
  content: string;
  mcpData?: any;
  usage?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private config: ChatConfig | null = null;
  private conversationHistory: Array<{role: string; content: string}> = [];

  constructor(private http: HttpClient) {
    // Load config from localStorage if exists
    const savedConfig = localStorage.getItem('chat-config');
    if (savedConfig) {
      try {
        this.config = JSON.parse(savedConfig);
      } catch (e) {
        console.error('Failed to parse saved chat config:', e);
      }
    }
  }

  configure(config: ChatConfig) {
    this.config = config;
    localStorage.setItem('chat-config', JSON.stringify(config));
  }

  getConfig(): ChatConfig | null {
    return this.config;
  }

  async sendMessage(message: string, mcpData?: any): Promise<ChatResponse> {
    if (!this.config) {
      throw new Error('Chat service not configured');
    }

    // For real-time queries like camera status, clear history to get fresh responses
    const isRealTimeQuery = message.toLowerCase().includes('camera') && 
                           (message.toLowerCase().includes('status') || 
                            message.toLowerCase().includes('detection') ||
                            message.toLowerCase().includes('results'));
    
    if (isRealTimeQuery && mcpData) {
      console.log('Real-time query detected, clearing conversation history for fresh response');
      this.conversationHistory = [];
    }

    // Add user message to history
    this.conversationHistory.push({ role: 'user', content: message });

    // Prepare the system message with MCP data if available
    const currentTime = new Date().toISOString();
    let systemMessage = `You are a helpful AI assistant integrated with the Local Console application for IMX500 smart cameras. Current time: ${currentTime}`;
    
    if (mcpData) {
      console.log('Including MCP data in system message:', mcpData);
      // Extract content from MCP response if it has the content structure
      let mcpContent = mcpData;
      if (mcpData.content && Array.isArray(mcpData.content)) {
        mcpContent = mcpData.content.map((item: any) => item.text || item).join('\n');
      }
      systemMessage += `\n\n🔴 LIVE DATA from IMX500 camera MCP server (retrieved at ${currentTime}):\n${typeof mcpContent === 'string' ? mcpContent : JSON.stringify(mcpContent, null, 2)}`;
      systemMessage += '\n\n⚠️ IMPORTANT: This is REAL-TIME data. Please provide a fresh analysis of the current detection results. Do not reference any previous camera status. Focus on the actual objects detected NOW, their confidence levels, and current camera mode.';
    }

    // Prepare messages for the API
    const messages = [
      { role: 'system', content: systemMessage },
      ...this.conversationHistory.slice(-10) // Keep last 10 messages for context
    ];

    try {
      let headers: HttpHeaders;
      let body: any;
      let assistantMessage: string;

      // Prepare headers based on provider
      const headerOptions: any = {
        'Content-Type': 'application/json'
      };

      if (this.config.provider !== 'ollama' && this.config.apiKey) {
        headerOptions['Authorization'] = `Bearer ${this.config.apiKey}`;
      }

      headers = new HttpHeaders(headerOptions);

      // Prepare request body (OpenAI-compatible format for all providers)
      body = {
        model: this.config.model || 'llama2:latest',
        messages,
        temperature: this.config.temperature || 0.7,
        max_tokens: this.config.maxTokens || 1000
      };

      console.log('Sending request to:', this.config.apiEndpoint);
      console.log('Request body:', JSON.stringify(body, null, 2));

      const response = await firstValueFrom(
        this.http.post<any>(this.config.apiEndpoint, body, { 
          headers,
          observe: 'response'
        })
      );

      console.log('Response received:', response);
      assistantMessage = response.body.choices[0].message.content;
      
      // Add assistant response to history
      this.conversationHistory.push({ role: 'assistant', content: assistantMessage });

      return {
        content: assistantMessage,
        mcpData,
        usage: undefined // Ollama doesn't provide token usage info
      };
    } catch (error) {
      console.error('Error calling chat API:', error);
      console.error('Config:', this.config);
      throw error;
    }
  }

  clearHistory() {
    this.conversationHistory = [];
  }

  getHistory() {
    return [...this.conversationHistory];
  }
}