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

import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatCardModule } from '@angular/material/card';
import { MatTabsModule } from '@angular/material/tabs';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Router } from '@angular/router';
import { ROUTER_LINKS } from '../../../core/config/routes';
import { ChatService, ChatConfig } from '../../../core/chat/chat.service';
import { McpService, McpConfig } from '../../../core/mcp/mcp.service';

@Component({
  selector: 'app-chat-settings',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatIconModule,
    MatInputModule,
    MatFormFieldModule,
    MatCardModule,
    MatTabsModule,
    MatSlideToggleModule,
    MatSelectModule,
    MatSnackBarModule,
  ],
  templateUrl: './chat-settings.screen.html',
  styleUrls: ['./chat-settings.screen.scss'],
})
export class ChatSettingsScreen implements OnInit {
  mcpForm: FormGroup;
  chatForm: FormGroup;
  isTestingMcp = false;
  isTestingChat = false;

  providers = [
    { value: 'openai', label: 'OpenAI', requiresKey: true },
    { value: 'ollama', label: 'Ollama (Local)', requiresKey: false },
    { value: 'groq', label: 'Groq (Free Tier)', requiresKey: true },
    { value: 'custom', label: 'Custom API', requiresKey: true },
  ];

  modelsByProvider: Record<string, Array<{value: string, label: string}>> = {
    openai: [
      { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
      { value: 'gpt-4', label: 'GPT-4' },
      { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
    ],
    ollama: [
      { value: 'llama2:latest', label: 'Llama 2 (Installed)' },
      { value: 'deepseek-coder:6.7b-base', label: 'DeepSeek Coder 6.7B (Installed)' },
      { value: 'mistral', label: 'Mistral' },
      { value: 'codellama', label: 'Code Llama' },
      { value: 'phi', label: 'Phi-2' },
      { value: 'neural-chat', label: 'Neural Chat' },
    ],
    groq: [
      { value: 'mixtral-8x7b-32768', label: 'Mixtral 8x7B' },
      { value: 'llama2-70b-4096', label: 'Llama2 70B' },
      { value: 'gemma-7b-it', label: 'Gemma 7B' },
    ],
    custom: []
  };

  availableModels = this.modelsByProvider['openai'];

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private chatService: ChatService,
    private mcpService: McpService,
    private snackBar: MatSnackBar
  ) {
    this.mcpForm = this.fb.group({
      serverUrl: ['ws://localhost:8765', Validators.required],
      apiKey: [''],
      timeout: [30000, [Validators.required, Validators.min(1000)]],
    });

    this.chatForm = this.fb.group({
      provider: ['ollama', Validators.required],
      apiEndpoint: ['http://localhost:11434/v1/chat/completions', Validators.required],
      apiKey: [''],
      model: ['llama2:latest', Validators.required],
      temperature: [0.7, [Validators.required, Validators.min(0), Validators.max(2)]],
      maxTokens: [1000, [Validators.required, Validators.min(1), Validators.max(4000)]],
    });
  }

  ngOnInit() {
    // Load existing configs
    const mcpConfig = this.mcpService.getConfig();
    if (mcpConfig) {
      this.mcpForm.patchValue(mcpConfig);
    }

    const chatConfig = this.chatService.getConfig();
    if (chatConfig) {
      this.chatForm.patchValue(chatConfig);
      // Update models based on loaded provider
      if (chatConfig.provider) {
        this.onProviderChange(chatConfig.provider);
      }
    } else {
      // Set initial models for default provider (ollama)
      this.onProviderChange('ollama');
    }

    // Listen for provider changes
    this.chatForm.get('provider')?.valueChanges.subscribe(provider => {
      this.onProviderChange(provider);
    });
  }

  onProviderChange(provider: string) {
    console.log('Provider changed to:', provider);
    const providerConfig = this.providers.find(p => p.value === provider);
    const apiKeyControl = this.chatForm.get('apiKey');
    const modelControl = this.chatForm.get('model');
    
    // Update available models
    this.availableModels = this.modelsByProvider[provider] || [];
    console.log('Available models updated:', this.availableModels);
    
    // Set default model for the provider and force update
    if (this.availableModels.length > 0) {
      const defaultModel = this.availableModels[0].value;
      console.log('Setting default model:', defaultModel);
      modelControl?.setValue(defaultModel);
      modelControl?.updateValueAndValidity();
    }
    
    // Update API endpoint based on provider
    switch (provider) {
      case 'openai':
        this.chatForm.patchValue({ apiEndpoint: 'https://api.openai.com/v1/chat/completions' });
        break;
      case 'ollama':
        this.chatForm.patchValue({ apiEndpoint: 'http://localhost:11434/v1/chat/completions' });
        break;
      case 'groq':
        this.chatForm.patchValue({ apiEndpoint: 'https://api.groq.com/openai/v1/chat/completions' });
        break;
    }
    
    // Update API key requirement
    if (providerConfig?.requiresKey) {
      apiKeyControl?.setValidators([Validators.required]);
    } else {
      apiKeyControl?.clearValidators();
    }
    apiKeyControl?.updateValueAndValidity();
  }

  async saveMcpSettings() {
    if (this.mcpForm.invalid) return;

    const config: McpConfig = this.mcpForm.value;
    const connected = await this.mcpService.connect(config);

    if (connected) {
      this.snackBar.open('MCP settings saved and connected successfully', 'OK', { duration: 3000 });
    } else {
      this.snackBar.open('Failed to connect to MCP server', 'OK', { duration: 3000 });
    }
  }

  saveChatSettings() {
    if (this.chatForm.invalid) return;

    const config: ChatConfig = this.chatForm.value;
    this.chatService.configure(config);
    this.snackBar.open('Chat settings saved successfully', 'OK', { duration: 3000 });
  }

  async testMcpConnection() {
    if (this.mcpForm.invalid) return;

    this.isTestingMcp = true;
    try {
      const config: McpConfig = this.mcpForm.value;
      const connected = await this.mcpService.connect(config);
      
      if (connected) {
        const tools = await this.mcpService.listTools();
        this.snackBar.open(`Connection successful! ${tools.length} tools available`, 'OK', { duration: 3000 });
      } else {
        this.snackBar.open('Connection failed', 'OK', { duration: 3000 });
      }
    } catch (error) {
      this.snackBar.open('Error occurred during connection test', 'OK', { duration: 3000 });
    } finally {
      this.isTestingMcp = false;
    }
  }

  async testChatConnection() {
    if (this.chatForm.invalid) return;

    this.isTestingChat = true;
    try {
      const config: ChatConfig = this.chatForm.value;
      this.chatService.configure(config);
      
      const response = await this.chatService.sendMessage('Hello, this is a test message.');
      this.snackBar.open('Connection successful! Response received', 'OK', { duration: 3000 });
    } catch (error) {
      this.snackBar.open('Error occurred during connection test', 'OK', { duration: 3000 });
    } finally {
      this.isTestingChat = false;
    }
  }

  goBack() {
    this.router.navigate([ROUTER_LINKS.CHAT_HUB]);
  }

  trackByValue(index: number, item: any): any {
    return item.value;
  }
}