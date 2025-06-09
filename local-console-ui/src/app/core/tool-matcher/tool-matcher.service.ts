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
import { ChatService } from '../chat/chat.service';
import { McpTool } from '../mcp/mcp.service';

export interface ToolMatchResult {
  tool: string;
  confidence: number;
  reason?: string;
  parameters?: Record<string, any>;
}

export interface ToolSuggestion {
  tool: McpTool;
  confidence: number;
  reason?: string;
}

@Injectable({
  providedIn: 'root'
})
export class ToolMatcherService {
  private feedbackHistory: Array<{
    query: string;
    tool: string;
    accepted: boolean;
    timestamp: Date;
  }> = [];

  constructor(private chatService: ChatService) {
    this.loadFeedbackHistory();
  }

  async matchTool(userQuery: string, availableTools: McpTool[]): Promise<ToolMatchResult> {
    // Step 1: Input validation
    if (!userQuery.trim()) {
      return { tool: 'none', confidence: 0, reason: 'Empty query' };
    }

    if (!availableTools || availableTools.length === 0) {
      return { tool: 'none', confidence: 0, reason: 'No tools available' };
    }

    // Step 2: Preprocess query
    const normalizedQuery = this.preprocessQuery(userQuery);

    // Step 3: Check for exact matches first (fast path)
    const exactMatch = this.checkExactMatch(normalizedQuery, availableTools);
    if (exactMatch) {
      return exactMatch;
    }

    // Step 4: Try LLM matching with timeout
    try {
      const llmResult = await this.withTimeout(
        this.performLLMMatching(normalizedQuery, availableTools),
        3000 // 3 second timeout
      );
      
      if (llmResult && llmResult.confidence > 0.3) {
        return llmResult;
      }
    } catch (e) {
      console.warn('LLM matching failed, falling back to simple matching:', e);
    }

    // Step 5: Fallback to simple matching
    return this.fallbackMatching(normalizedQuery, availableTools);
  }

  recordFeedback(query: string, tool: string, accepted: boolean): void {
    const feedback = {
      query: query.toLowerCase().trim(),
      tool,
      accepted,
      timestamp: new Date()
    };

    this.feedbackHistory.push(feedback);
    this.saveFeedbackHistory();
  }

  private async performLLMMatching(query: string, tools: McpTool[]): Promise<ToolMatchResult> {
    const toolsInfo = this.formatToolsForLLM(tools);
    const prompt = this.createMatchingPrompt(query, toolsInfo);
    
    // Use the existing ChatService to send a raw prompt
    const chatConfig = this.chatService.getConfig();
    if (!chatConfig) {
      throw new Error('Chat service not configured');
    }

    try {
      // Create a direct API call without going through the normal chat flow
      const response = await this.sendRawLLMRequest(prompt, chatConfig);
      
      // Extract JSON from response (handle markdown code blocks)
      const jsonString = this.extractJSON(response);
      const parsed = JSON.parse(jsonString);
      
      // Validate the response
      if (parsed.tool && typeof parsed.confidence === 'number') {
        // Ensure the tool exists in available tools
        const toolExists = tools.find(t => t.name === parsed.tool);
        if (toolExists || parsed.tool === 'none') {
          return {
            tool: parsed.tool,
            confidence: Math.max(0, Math.min(1, parsed.confidence)),
            reason: parsed.reason || 'LLM matching',
            parameters: parsed.parameters || {}
          };
        }
      }
      
      throw new Error('Invalid LLM response format');
    } catch (e) {
      console.error('LLM matching error:', e);
      throw e;
    }
  }

  private formatToolsForLLM(tools: McpTool[]): string {
    return tools.map(tool => 
      `Tool: ${tool.name}
Description: ${tool.description || 'No description available'}
Parameters: ${tool.inputSchema ? JSON.stringify(tool.inputSchema.properties || {}) : 'None'}`
    ).join('\n\n');
  }

  private createMatchingPrompt(userQuery: string, toolsInfo: string): string {
    return `You are a tool matcher. Match the user's intent to the most appropriate tool.

User Query: "${userQuery}"

Available Tools:
${toolsInfo}

Instructions:
1. Analyze the user's intent, not just keywords
2. Consider synonyms and related concepts
3. If the query is in a non-English language, understand the intent
4. Return ONLY a valid JSON object (no markdown, no code blocks, no explanation):

{
  "tool": "exact_tool_name_or_none",
  "confidence": 0.0-1.0,
  "reason": "brief explanation of why this tool matches",
  "parameters": {"param_name": "param_value"}
}

Confidence scoring:
- 1.0: Perfect match (exact tool name or clear intent)
- 0.8-0.9: High confidence (main keywords match)
- 0.6-0.7: Medium confidence (partial match or related concept)  
- 0.3-0.5: Low confidence (vague similarity)
- 0.0-0.2: No match

Examples:
- "camera status" → {"tool": "camera_status", "confidence": 1.0, "reason": "Direct match", "parameters": {}}
- "switch to classification" → {"tool": "switch_model", "confidence": 0.9, "reason": "Model switching", "parameters": {"model_type": "classification"}}
- "change to detection mode" → {"tool": "switch_model", "confidence": 0.9, "reason": "Model switching", "parameters": {"model_type": "detection"}}
- "カメラの状態" → {"tool": "camera_status", "confidence": 0.9, "reason": "Japanese for camera status", "parameters": {}}
- "hello" → {"tool": "none", "confidence": 0.0, "reason": "Greeting, not a tool request", "parameters": {}}`;
  }

  private async sendRawLLMRequest(prompt: string, chatConfig: any): Promise<string> {
    const body = {
      model: chatConfig.model || 'llama2:latest',
      messages: [
        { role: 'user', content: prompt }
      ],
      temperature: 0.1, // Low temperature for consistent tool matching
      max_tokens: 200   // Short response for JSON
    };

    const headers: any = {
      'Content-Type': 'application/json'
    };

    if (chatConfig.provider !== 'ollama' && chatConfig.apiKey) {
      headers['Authorization'] = `Bearer ${chatConfig.apiKey}`;
    }

    const response = await fetch(chatConfig.apiEndpoint, {
      method: 'POST',
      headers,
      body: JSON.stringify(body)
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return data.choices[0].message.content;
  }

  private withTimeout<T>(promise: Promise<T>, timeoutMs: number): Promise<T> {
    return Promise.race([
      promise,
      new Promise<T>((_, reject) => 
        setTimeout(() => reject(new Error('Timeout')), timeoutMs)
      )
    ]);
  }

  private extractJSON(text: string): string {
    // Try to extract JSON from markdown code blocks or plain text
    
    // First, try to find JSON in code blocks
    const codeBlockMatch = text.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/i);
    if (codeBlockMatch) {
      return codeBlockMatch[1].trim();
    }
    
    // Second, try to find JSON object in the text
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      return jsonMatch[0].trim();
    }
    
    // Third, if the text looks like it starts and ends with braces, use it directly
    const trimmed = text.trim();
    if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
      return trimmed;
    }
    
    // If nothing works, throw error with more context
    console.warn('Failed to extract JSON from LLM response:', text);
    throw new Error(`Could not extract JSON from response: ${text.substring(0, 100)}...`);
  }

  private preprocessQuery(query: string): string {
    return query
      .trim()
      .toLowerCase()
      .replace(/[！？。、]/g, '') // Remove Japanese punctuation
      .replace(/\s+/g, ' ');      // Normalize whitespace
  }

  private checkExactMatch(query: string, tools: McpTool[]): ToolMatchResult | null {
    // Check for exact tool name match
    for (const tool of tools) {
      if (query === tool.name.toLowerCase()) {
        return {
          tool: tool.name,
          confidence: 1.0,
          reason: 'Exact tool name match',
          parameters: {}
        };
      }

      // Check for exact match with underscores/hyphens removed
      const normalizedToolName = tool.name.toLowerCase().replace(/[_-]/g, '');
      const normalizedQuery = query.replace(/[_-\s]/g, '');
      
      if (normalizedQuery === normalizedToolName) {
        return {
          tool: tool.name,
          confidence: 0.95,
          reason: 'Normalized exact match',
          parameters: {}
        };
      }
    }

    return null;
  }

  private fallbackMatching(query: string, tools: McpTool[]): ToolMatchResult {
    const scores = tools.map(tool => {
      const tokens = tool.name.toLowerCase().split(/[_-]/);
      let score = 0;

      // Check if query contains tool name tokens
      for (const token of tokens) {
        if (query.includes(token)) {
          score += 0.3;
        }
      }

      // Check description if available
      if (tool.description) {
        const descTokens = tool.description.toLowerCase().split(/\s+/);
        for (const token of descTokens) {
          if (query.includes(token) && token.length > 2) {
            score += 0.1;
          }
        }
      }

      // Apply learning boost from feedback
      const boost = this.getConfidenceBoost(query, tool.name);
      score += boost;

      return {
        tool: tool.name,
        confidence: Math.min(score, 0.8), // Fallback max confidence is 0.8
        reason: `Token matching (${tokens.join(', ')})`
      };
    });

    // Return the highest scoring tool
    const bestMatch = scores.reduce((best, current) => 
      current.confidence > best.confidence ? current : best
    );

    if (bestMatch.confidence > 0.2) {
      return {
        ...bestMatch,
        parameters: {}
      };
    } else {
      return {
        tool: 'none',
        confidence: 0,
        reason: 'No sufficient match found',
        parameters: {}
      };
    }
  }

  private getConfidenceBoost(query: string, toolName: string): number {
    const similar = this.feedbackHistory.filter(h => 
      this.isSimilar(h.query, query) && 
      h.tool === toolName && 
      h.accepted
    );

    return Math.min(similar.length * 0.05, 0.2);
  }

  private isSimilar(query1: string, query2: string): boolean {
    // Simple similarity check - can be improved later
    const words1 = query1.split(/\s+/);
    const words2 = query2.split(/\s+/);
    
    const commonWords = words1.filter(word => 
      words2.includes(word) && word.length > 2
    );

    return commonWords.length >= Math.min(words1.length, words2.length) * 0.5;
  }

  private loadFeedbackHistory(): void {
    try {
      const saved = localStorage.getItem('tool-match-feedback');
      if (saved) {
        const parsed = JSON.parse(saved);
        this.feedbackHistory = parsed.map((item: any) => ({
          ...item,
          timestamp: new Date(item.timestamp)
        }));
      }
    } catch (e) {
      console.error('Failed to load tool matcher feedback history:', e);
      this.feedbackHistory = [];
    }
  }

  private saveFeedbackHistory(): void {
    try {
      // Keep only recent feedback (last 100 items)
      const recentFeedback = this.feedbackHistory.slice(-100);
      localStorage.setItem('tool-match-feedback', JSON.stringify(recentFeedback));
      this.feedbackHistory = recentFeedback;
    } catch (e) {
      console.error('Failed to save tool matcher feedback history:', e);
    }
  }
}