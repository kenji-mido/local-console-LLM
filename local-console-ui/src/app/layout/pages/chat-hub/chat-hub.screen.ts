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

import { Component, OnInit, OnDestroy, signal, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatCardModule } from '@angular/material/card';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatMenuModule } from '@angular/material/menu';
import { Router } from '@angular/router';
import { ROUTER_LINKS } from '../../../core/config/routes';
import { ChatService } from '../../../core/chat/chat.service';
import { McpService } from '../../../core/mcp/mcp.service';

export interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  mcpData?: any;
}

@Component({
  selector: 'app-chat-hub',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatIconModule,
    MatInputModule,
    MatFormFieldModule,
    MatCardModule,
    MatToolbarModule,
    MatMenuModule,
  ],
  templateUrl: './chat-hub.screen.html',
  styleUrls: ['./chat-hub.screen.scss'],
})
export class ChatHubScreen implements OnInit, OnDestroy, AfterViewChecked {
  @ViewChild('messagesContainer') messagesContainer!: ElementRef;
  @ViewChild('chatInput') chatInput!: ElementRef;
  
  messages = signal<ChatMessage[]>([]);
  inputMessage = '';
  isLoading = signal(false);
  mcpConnected = signal(false);
  expandedMcpData = new Set<string>();
  private shouldScrollToBottom = false;

  constructor(
    private chatService: ChatService,
    private mcpService: McpService,
    private router: Router
  ) {}

  ngOnInit() {
    // Expose chat service to window for debugging
    (window as any).chatService = this.chatService;
    
    // Subscribe to MCP connection status
    this.mcpService.connectionStatus$.subscribe(status => {
      this.mcpConnected.set(status);
    });

    // Load conversation history from service
    const history = this.chatService.getHistory();
    
    if (history.length > 0) {
      // Convert service history format to component message format
      const messages: ChatMessage[] = history.map((msg, index) => ({
        id: this.generateId() + '_' + index,
        content: msg.content,
        role: msg.role as 'user' | 'assistant',
        timestamp: new Date() // We don't store timestamps in service, so use current time
      }));
      this.messages.set(messages);
      this.shouldScrollToBottom = true;
    } else {
      // Load and apply chat configuration
      const chatConfig = this.chatService.getConfig();
      if (!chatConfig) {
        // Show configuration needed message
        this.messages.update(msgs => [...msgs, {
          id: this.generateId(),
          content: 'Please configure your LLM settings first by clicking the settings menu (⋮) and selecting "MCP Settings".',
          role: 'assistant',
          timestamp: new Date()
        }]);
      } else {
        // Check if this is truly the first time (no messages at all)
        // We don't want to add welcome message if user cleared the chat
        const hasNeverHadMessages = localStorage.getItem('chat-has-messages') !== 'true';
        
        if (hasNeverHadMessages) {
          // Add welcome message
          this.messages.update(msgs => [...msgs, {
            id: this.generateId(),
            content: 'Hello! I am your AI assistant. I can help you with various information by connecting to MCP servers.',
            role: 'assistant',
            timestamp: new Date()
          }]);
        }
      }
    }
  }

  async sendMessage() {
    if (!this.inputMessage.trim()) return;

    // Check if chat service is configured
    const chatConfig = this.chatService.getConfig();
    if (!chatConfig) {
      const errorMessage: ChatMessage = {
        id: this.generateId(),
        content: 'Please configure your LLM settings first by going to Settings.',
        role: 'assistant',
        timestamp: new Date()
      };
      this.messages.update(msgs => [...msgs, errorMessage]);
      return;
    }


    const userMessage: ChatMessage = {
      id: this.generateId(),
      content: this.inputMessage,
      role: 'user',
      timestamp: new Date()
    };

    this.messages.update(msgs => [...msgs, userMessage]);
    this.inputMessage = '';
    this.isLoading.set(true);
    this.shouldScrollToBottom = true;
    
    // Mark that the user has sent messages
    localStorage.setItem('chat-has-messages', 'true');

    try {
      // Get MCP data if connected
      let mcpData = null;
      
      if (this.mcpConnected()) {
        try {
          // Check if user is asking for camera status or detection specifically
          const isRealTimeQuery = userMessage.content.toLowerCase().includes('camera') && 
                                 (userMessage.content.toLowerCase().includes('status') || 
                                  userMessage.content.toLowerCase().includes('detection') ||
                                  userMessage.content.toLowerCase().includes('results'));
          
          if (isRealTimeQuery) {
            mcpData = await this.mcpService.callTool('camera_status', {});
          } else {
            mcpData = await this.mcpService.queryData(userMessage.content);
          }
        } catch (mcpError) {
          console.error('MCP query failed:', mcpError);
          // Continue without MCP data
        }
      }

      // Send to chat service
      const response = await this.chatService.sendMessage(userMessage.content, mcpData);

      const assistantMessage: ChatMessage = {
        id: this.generateId(),
        content: response.content,
        role: 'assistant',
        timestamp: new Date(),
        mcpData: response.mcpData
      };

      this.messages.update(msgs => [...msgs, assistantMessage]);
      this.shouldScrollToBottom = true;
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: ChatMessage = {
        id: this.generateId(),
        content: 'An error occurred. Please try again.',
        role: 'assistant',
        timestamp: new Date()
      };
      this.messages.update(msgs => [...msgs, errorMessage]);
      this.shouldScrollToBottom = true;
    } finally {
      this.isLoading.set(false);
      // Restore focus to input field after response
      this.focusInput();
    }
  }

  openSettings() {
    this.router.navigate([ROUTER_LINKS.CHAT_SETTINGS]);
  }

  clearChat() {
    // Clear history in service as well
    this.chatService.clearHistory();
    
    // Reset the has-messages flag so welcome message won't show next time
    localStorage.setItem('chat-has-messages', 'true');
    
    this.messages.set([{
      id: this.generateId(),
      content: 'Chat history cleared. Let\'s start a new conversation!',
      role: 'assistant',
      timestamp: new Date()
    }]);
    this.shouldScrollToBottom = true;
  }

  ngAfterViewChecked() {
    if (this.shouldScrollToBottom) {
      this.scrollToBottom();
      this.shouldScrollToBottom = false;
    }
  }

  ngOnDestroy() {
    // Clean up debug references
    if ((window as any).chatService === this.chatService) {
      delete (window as any).chatService;
    }
  }

  private scrollToBottom(): void {
    try {
      if (this.messagesContainer) {
        const element = this.messagesContainer.nativeElement;
        element.scrollTop = element.scrollHeight;
      }
    } catch (err) {
      console.error('Error scrolling to bottom');
    }
  }

  toggleMcpData(messageId: string) {
    if (this.expandedMcpData.has(messageId)) {
      this.expandedMcpData.delete(messageId);
    } else {
      this.expandedMcpData.add(messageId);
    }
  }

  isExpandedMcpData(messageId: string): boolean {
    return this.expandedMcpData.has(messageId);
  }

  formatMcpData(mcpData: any): string {
    try {
      // If mcpData has content array structure, extract text content
      if (mcpData && mcpData.content && Array.isArray(mcpData.content)) {
        const textContent = mcpData.content
          .map((item: any) => {
            if (typeof item === 'string') return item;
            if (item.text) return item.text;
            if (item.type === 'text' && item.text) return item.text;
            return JSON.stringify(item, null, 2);
          })
          .join('\n');
        
        return textContent || JSON.stringify(mcpData, null, 2);
      }
      
      // For other data structures
      if (typeof mcpData === 'string') {
        return mcpData;
      }
      
      return JSON.stringify(mcpData, null, 2);
    } catch (error) {
      return 'Error formatting MCP data: ' + String(mcpData);
    }
  }

  getCurrentModel(): string {
    const config = this.chatService.getConfig();
    if (config && config.model) {
      // Show friendly name for installed models
      const modelName = config.model;
      if (modelName === 'llama2:latest') return 'Llama 2';
      if (modelName === 'gemma3:4b') return 'Gemma 3 4B';
      if (modelName === 'qwen3:8b') return 'Qwen 3 8B';
      return modelName;
    }
    return 'No model selected';
  }

  sendModelTestMessage() {
    this.inputMessage = 'What model are you?';
    this.sendMessage();
  }

  testModelSwitch() {
    const config = this.chatService.getConfig();
    if (config) {
      this.inputMessage = `Please confirm: What model are you running as? I expect you to say "${config.model}".`;
      this.sendMessage();
    }
  }

  private focusInput(): void {
    // Use setTimeout to ensure DOM is updated before focusing
    setTimeout(() => {
      try {
        if (this.chatInput && this.chatInput.nativeElement) {
          this.chatInput.nativeElement.focus();
        }
      } catch (error) {
        console.log('Could not focus input');
      }
    }, 100);
  }

  private generateId(): string {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
  }
}