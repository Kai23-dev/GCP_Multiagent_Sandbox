'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { SparklesIcon, XMarkIcon } from '@heroicons/react/24/outline';
import {
  Bot, User, Settings, Send, Clock, CheckCircle,
  Copy, RefreshCw, Mic, MicOff, Trophy, Star, Brain,
  Sparkles, Rocket, Target, Flame, Award, Gift
} from 'lucide-react';
import clsx from 'clsx';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import 'highlight.js/styles/github-dark.css';
import { useConfig } from '@/hooks/useConfig';
import { useTheme } from '@/hooks/useTheme';
import { getAvailableThemes } from '@/styles/themes';

// Interface for memory data structure
interface MemoryData {
  memory?: {
    content?: {
      parts?: Array<{ text?: string }>;
    } | string;
    text?: string;
    summary?: string;
    author?: string;
    title?: string;
    timestamp?: string | number;
    created_at?: string | number;
    relevance_score?: number;
    score?: number;
  };
  content?: {
    parts?: Array<{ text?: string }>;
  } | string;
  text?: string;
  summary?: string;
  author?: string;
  title?: string;
  timestamp?: string | number;
  created_at?: string | number;
  relevance_score?: number;
  score?: number;
}

// Types
type BackendType = 'agent-engine' | 'dialogflow-cx' | 'vertex-ai';

interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  backend?: BackendType;
  status?: 'sending' | 'sent' | 'error' | 'streaming';
  intent?: string;
  confidence?: number;
  isTyping?: boolean;
}

interface ChatSettings {
  backend: BackendType;
  agentId?: string;
  dialogflowAgentId?: string;
  dataStoreId?: string;
  model?: string;
  temperature?: number;
  languageCode?: string;
  enableStreaming?: boolean;
}

interface Agent {
  id: string;
  display_name: string;
  description: string;
  create_time: string;
  update_time: string;
  state: string;
}

interface DialogflowAgent {
  id: string;
  name: string;
  display_name: string;
  description: string;
  time_zone: string;
  default_language_code: string;
  supported_language_codes: string[];
  avatar_uri: string;
  enable_stackdriver_logging: boolean;
  enable_spell_checking: boolean;
}

// Instagram-style Story Bubbles for Agents
const AgentStoryBubble = ({ agent, isActive, onClick }: {
  agent: Agent | DialogflowAgent;
  isActive: boolean;
  onClick: () => void;
}) => (
  <button
    onClick={onClick}
    className={clsx(
      "flex flex-col items-center space-y-1 cursor-pointer transition-all",
      "hover:scale-105 active:scale-95"
    )}
  >
    <div className={clsx(
      "relative w-16 h-16 rounded-full p-0.5",
      isActive
        ? "bg-gradient-to-tr from-yellow-400 via-pink-500 to-purple-600"
        : "bg-gradient-to-tr from-gray-300 to-gray-400"
    )}>
      <div className="w-full h-full bg-white rounded-full p-0.5">
        <div className={clsx(
          "w-full h-full rounded-full flex items-center justify-center",
          "bg-gradient-to-br from-purple-500 to-pink-500"
        )}>
          <Bot className="w-6 h-6 text-white" />
        </div>
      </div>
      {isActive && (
        <div className="absolute -bottom-1 -right-1 w-5 h-5 bg-green-500 rounded-full border-2 border-white flex items-center justify-center">
          <CheckCircle className="w-3 h-3 text-white" />
        </div>
      )}
    </div>
    <span className="text-xs font-medium text-gray-700 max-w-16 truncate">
      {agent.display_name}
    </span>
  </button>
);

// Enhanced Typing Indicator with more personality
const TypingIndicator = () => (
  <div className="flex items-center space-x-2 px-4 py-3 bg-white rounded-3xl shadow-lg border border-gray-100 max-w-24">
    <div className="flex space-x-1">
      <div className="w-2.5 h-2.5 bg-gradient-to-r from-purple-400 to-pink-400 rounded-full animate-bounce"></div>
      <div className="w-2.5 h-2.5 bg-gradient-to-r from-pink-400 to-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
      <div className="w-2.5 h-2.5 bg-gradient-to-r from-purple-400 to-pink-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
    </div>
  </div>
);

// Gamification Badge Component
const GamificationBadge = ({ type, label }: { type: string; label: string }) => {
  const icons = {
    streak: Flame,
    level: Trophy,
    achievement: Award,
    xp: Star,
    bonus: Gift,
  };

  const Icon = icons[type as keyof typeof icons] || Star;

  return (
    <div className={clsx(
      "inline-flex items-center space-x-1 px-3 py-1 rounded-full text-xs font-semibold",
      "bg-gradient-to-r from-yellow-400 to-orange-400 text-white shadow-md",
      "animate-pulse-slow"
    )}>
      <Icon className="w-3 h-3" />
      <span>{label}</span>
    </div>
  );
};

// Simplified Message Bubble with just copy button
const MessageBubble = ({
  message,
  onCopy
}: {
  message: Message;
  onCopy: (content: string) => void;
}) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    onCopy(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={clsx(
      'flex items-start space-x-3 group animate-fade-in-up',
      isUser ? 'justify-end' : 'justify-start'
    )}>
      {!isUser && (
        <div className="flex-shrink-0">
          <div className={clsx(
            "w-10 h-10 rounded-full flex items-center justify-center",
            "bg-gradient-to-br from-purple-500 to-pink-500",
            "shadow-lg ring-2 ring-white"
          )}>
            <Bot className="w-5 h-5 text-white" />
          </div>
        </div>
      )}

      <div className="relative max-w-sm lg:max-w-3xl">
        <div className={clsx(
          'px-5 py-3 rounded-3xl shadow-lg relative transition-all',
          'hover:shadow-xl',
          isUser
            ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white'
            : 'bg-white border border-gray-100 text-gray-800'
        )}>
          {/* Message content */}
          <div className="break-words markdown-content">
            {message.isTyping ? (
              <TypingIndicator />
            ) : (
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight, rehypeRaw]}
              >
                {message.content}
              </ReactMarkdown>
            )}
          </div>

          {/* Copy button */}
          <button
            onClick={handleCopy}
            className={clsx(
              'absolute top-2 right-2 p-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-all',
              isUser ? 'hover:bg-white/20' : 'hover:bg-gray-100'
            )}
            title="Copy message"
          >
            {copied ? (
              <CheckCircle className="w-4 h-4 text-green-500" />
            ) : (
              <Copy className={clsx('w-4 h-4', isUser ? 'text-white/70' : 'text-gray-400')} />
            )}
          </button>
        </div>

        {/* Timestamp and metadata */}
        <div className={clsx(
          'flex items-center space-x-2 mt-1 px-2 text-xs',
          isUser ? 'text-gray-600 justify-end' : 'text-gray-500'
        )}>
          <Clock className="w-3 h-3" />
          <span>{message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
          {message.status === 'streaming' && (
            <span className="text-purple-500 font-medium animate-pulse">Live</span>
          )}
          {message.backend && (
            <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full text-[10px] font-medium">
              {message.backend === 'agent-engine' ? 'Agent' :
               message.backend === 'dialogflow-cx' ? 'Dialogflow' : 'AI'}
            </span>
          )}
        </div>
      </div>

      {isUser && (
        <div className="flex-shrink-0">
          <div className={clsx(
            "w-10 h-10 rounded-full flex items-center justify-center",
            "bg-gradient-to-br from-blue-500 to-purple-500",
            "shadow-lg ring-2 ring-white"
          )}>
            <User className="w-5 h-5 text-white" />
          </div>
        </div>
      )}
    </div>
  );
};

// Main Enhanced Chat Interface
export default function ChatInterfaceEnhanced() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [sessionId, setSessionId] = useState<string>();
  const [isListening, setIsListening] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [dialogflowAgents, setDialogflowAgents] = useState<DialogflowAgent[]>([]);
  const [loadingAgents, setLoadingAgents] = useState(false);
  const [loadingDialogflowAgents, setLoadingDialogflowAgents] = useState(false);
  const [userStreak, setUserStreak] = useState(0);
  const [userLevel, setUserLevel] = useState(1);
  const [userXP, setUserXP] = useState(0);
  const [savingToMemory, setSavingToMemory] = useState(false);
  const [memorySaved, setMemorySaved] = useState(false);
  const [showMemoryBrowser, setShowMemoryBrowser] = useState(false);
  const [searchingMemories, setSearchingMemories] = useState(false);
  const [memories, setMemories] = useState<MemoryData[]>([]);
  const [memorySearchQuery, setMemorySearchQuery] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Get runtime configuration (for project info, environment flags)
  const { config } = useConfig();
  console.log('Runtime config:', config); // Used for debugging environment

  // Theme management
  const { theme, setTheme } = useTheme();
  const [showThemeSelector, setShowThemeSelector] = useState(false);

  // No client-side auth needed - IAP handles authentication
  // Backend APIs use service account credentials with user context from IAP headers

  const [settings, setSettings] = useState<ChatSettings>({
    backend: 'agent-engine',
    agentId: '',
    dialogflowAgentId: '',
    dataStoreId: '',
    model: 'gemini-2.0-flash',
    temperature: 0.7,
    languageCode: 'en',
    enableStreaming: true,
  });

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 120) + 'px';
    }
  }, [input]);

  // Gamification: Update streak and XP
  useEffect(() => {
    const messageCount = messages.filter(m => m.role === 'user').length;
    setUserStreak(Math.min(messageCount, 7)); // Max 7-day streak visual
    setUserXP(messageCount * 10);
    setUserLevel(Math.floor(messageCount / 5) + 1);
  }, [messages]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const fetchAgents = useCallback(async () => {
    setLoadingAgents(true);
    try {
      // No auth headers needed - backend uses service account + IAP
      const response = await fetch('/api/agents');
      if (!response.ok) {
        throw new Error('Failed to fetch agents');
      }
      const data = await response.json();
      if (data.success && data.agents) {
        setAgents(data.agents);

        // Auto-select the first agent if none is selected
        if (!settings.agentId && data.agents.length > 0) {
          setSettings(prev => ({ ...prev, agentId: data.agents[0].id }));
        }
      }
    } catch (error) {
      console.error('Error fetching agents:', error);
    } finally {
      setLoadingAgents(false);
    }
  }, [settings.agentId]);

  const fetchDialogflowAgents = useCallback(async () => {
    setLoadingDialogflowAgents(true);
    try {
      const response = await fetch('/api/dialogflow-agents');
      if (!response.ok) {
        throw new Error('Failed to fetch Dialogflow agents');
      }
      const data = await response.json();
      if (data.success && data.agents) {
        setDialogflowAgents(data.agents);

        // Auto-select the first agent if none is selected
        if (!settings.dialogflowAgentId && data.agents.length > 0) {
          setSettings(prev => ({ ...prev, dialogflowAgentId: data.agents[0].id }));
        }
      }
    } catch (error) {
      console.error('Error fetching Dialogflow agents:', error);
    } finally {
      setLoadingDialogflowAgents(false);
    }
  }, [settings.dialogflowAgentId]);

  // Fetch agents when component mounts or when backend changes
  useEffect(() => {
    if (settings.backend === 'agent-engine') {
      fetchAgents();
    } else if (settings.backend === 'dialogflow-cx') {
      fetchDialogflowAgents();
    }
  }, [settings.backend, fetchAgents, fetchDialogflowAgents]);

  // Auto-select Demo Agent when agents are loaded
  useEffect(() => {
    if (!settings.agentId && agents.length > 0) {
      // Find Demo Agent (non-ADK)
      const demoAgent = agents.find(a =>
        a.display_name?.toLowerCase().includes('demo') &&
        !a.display_name?.toLowerCase().includes('adk')
      );

      if (demoAgent) {
        setSettings(prev => ({ ...prev, agentId: demoAgent.id }));
        console.log('Auto-selected Demo Agent:', demoAgent.display_name);
      } else {
        // If no Demo Agent, try to find any non-ADK agent
        const nonAdkAgent = agents.find(a =>
          !a.display_name?.toLowerCase().includes('adk')
        );
        if (nonAdkAgent) {
          setSettings(prev => ({ ...prev, agentId: nonAdkAgent.id }));
          console.log('Auto-selected non-ADK agent:', nonAdkAgent.display_name);
        }
      }
    }
  }, [agents, settings.agentId]);

  // Save conversation to Agent Engine Memory Bank
  const saveToMemoryBank = async () => {
    if (!settings.agentId || settings.backend !== 'agent-engine') {
      alert('Memory bank is only available for Agent Engine agents');
      return;
    }

    if (messages.length === 0) {
      alert('No conversation to save');
      return;
    }

    setSavingToMemory(true);
    try {
      if (!sessionId) {
        alert('No active session to save. Start a conversation first!');
        return;
      }

      const memoryPayload = {
        agentId: settings.agentId,
        sessionId: sessionId,
        action: 'save' as const,
      };

      const response = await fetch('/api/agent-memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(memoryPayload)
      });

      if (!response.ok) {
        throw new Error('Failed to save to memory bank');
      }

      const result = await response.json();

      setMemorySaved(true);
      setTimeout(() => setMemorySaved(false), 5000);

      // Show success message in chat with memory ID
      const memoryMessage: Message = {
        id: Date.now().toString(),
        content: `🧠 **Session saved to Memory Bank!**\n\nThe agent will remember this conversation in future interactions. Memory ID: \`${result.memoryId || sessionId}\`\n\nYou can search your memories anytime using the Memory Browser.`,
        role: 'assistant',
        timestamp: new Date(),
        backend: 'agent-engine',
        status: 'sent'
      };
      setMessages(prev => [...prev, memoryMessage]);

      // Add XP boost for saving to memory
      setUserXP(prev => prev + 50);

    } catch (error) {
      console.error('Failed to save to memory bank:', error);
      const errorMsg: Message = {
        id: Date.now().toString(),
        content: `❌ Failed to save to memory bank: ${error instanceof Error ? error.message : 'Unknown error'}`,
        role: 'assistant',
        timestamp: new Date(),
        backend: 'agent-engine',
        status: 'error'
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setSavingToMemory(false);
    }
  };

  // Load memory as active conversation
  const loadMemory = async (memory: MemoryData) => {
    if (!settings.agentId) return;

    try {
      // Extract content from the memory
      const memoryData = memory.memory || memory;
      let content = '';
      if (typeof memoryData.content === 'object' && memoryData.content?.parts?.[0]?.text) {
        content = memoryData.content.parts[0].text;
      } else if (memoryData.content && typeof memoryData.content === 'string') {
        content = memoryData.content;
      } else if (memoryData.text) {
        content = memoryData.text;
      }

      if (!content) {
        alert('Could not extract content from memory');
        return;
      }

      const author = memoryData.author || 'user';
      
      // Add the memory as a message in the current chat
      const newMessage: Message = {
        id: Date.now().toString(),
        content: content,
        role: author === 'user' ? 'user' : 'assistant',
        timestamp: new Date(memoryData.timestamp || Date.now()),
        backend: 'agent-engine',
        status: 'sent'
      };

      setMessages(prev => [...prev, newMessage]);
      setShowMemoryBrowser(false);
      
      // Show success notification
      const successMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `📥 **Memory Loaded!**\n\nThis message was restored from your memory bank. You can continue the conversation from here.`,
        role: 'assistant',
        timestamp: new Date(),
        backend: 'agent-engine',
        status: 'sent'
      };
      setMessages(prev => [...prev, successMessage]);

    } catch (error) {
      console.error('Failed to load memory:', error);
      alert('Failed to load memory. Please try again.');
    }
  };

  // Search memories
  const searchMemories = async (query: string) => {
    if (!settings.agentId || !query.trim()) {
      return;
    }

    setSearchingMemories(true);
    try {
      const response = await fetch('/api/agent-memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agentId: settings.agentId,
          action: 'search',
          query: query.trim(),
        })
      });

      if (!response.ok) {
        throw new Error('Failed to search memories');
      }

      const result = await response.json();
      console.log('Memory search response:', result);
      
      if (result.success && result.memories) {
        setMemories(result.memories);
        console.log(`Loaded ${result.memories.length} memories`);
      } else {
        console.warn('No memories in response:', result);
        setMemories([]);
      }

    } catch (error) {
      console.error('Failed to search memories:', error);
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      alert(`Failed to search memories: ${errorMsg}`);
    } finally {
      setSearchingMemories(false);
    }
  };

  // Enhanced send message with streaming support
  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: input.trim(),
      role: 'user',
      timestamp: new Date(),
      status: 'sending',
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    // Add assistant typing message
    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      content: '',
      role: 'assistant',
      timestamp: new Date(),
      backend: settings.backend,
      status: 'streaming',
      isTyping: true,
    };

    setMessages(prev => [...prev, assistantMessage]);

    // Update message status to sent
    setTimeout(() => {
      setMessages(prev => prev.map(msg =>
        msg.id === userMessage.id ? { ...msg, status: 'sent' } : msg
      ));
    }, 500);

    try {
      // Check if streaming is enabled for agent engine
      const useStreaming = settings.backend === 'agent-engine' && settings.enableStreaming !== false;
      let response;

      switch (settings.backend) {
        case 'agent-engine':
          if (!settings.agentId) {
            throw new Error('Please select an agent first');
          }

          if (useStreaming) {
            // Use streaming endpoint for better performance
            response = await fetch('/api/agent-engine-stream', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                message: input.trim(),
                agentId: settings.agentId,
                sessionId,
              }),
            });

            if (response.ok && response.body) {
              // Handle streaming response
              const reader = response.body.getReader();
              const decoder = new TextDecoder();
              let accumulatedContent = '';
              let streamSessionId: string | undefined;

              while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n').filter(line => line.trim());

                for (const line of lines) {
                  if (line.startsWith('data: ')) {
                    try {
                      const data = JSON.parse(line.slice(6));
                      if (data.type === 'chunk') {
                        accumulatedContent += data.content;
                        setMessages(prev => prev.map(msg =>
                          msg.id === assistantMessage.id
                            ? { ...msg, content: accumulatedContent, isTyping: false }
                            : msg
                        ));
                      } else if (data.type === 'end') {
                        // Capture sessionId from end event
                        if (data.sessionId) {
                          streamSessionId = data.sessionId;
                        }
                        setMessages(prev => prev.map(msg =>
                          msg.id === assistantMessage.id
                            ? { ...msg, status: 'sent', isTyping: false }
                            : msg
                        ));
                      } else if (data.type === 'error') {
                        throw new Error(data.message);
                      }
                    } catch (e) {
                      console.error('Error parsing streaming chunk:', e);
                    }
                  }
                }
              }
              
              // Set session ID after streaming completes
              if (streamSessionId) {
                setSessionId(streamSessionId);
                console.log('Session ID set from stream:', streamSessionId);
              }
              
              return; // Exit early for streaming
            }
          } else {
            // Use regular endpoint
            response = await fetch('/api/agent-engine', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                message: input.trim(),
                agentId: settings.agentId,
                sessionId,
              }),
            });
          }
          break;

        case 'dialogflow-cx':
          if (!settings.dialogflowAgentId) {
            throw new Error('Please select a Dialogflow agent first');
          }
          response = await fetch('/api/dialogflow-cx', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              message: input.trim(),
              agentId: settings.dialogflowAgentId,
              sessionId,
              languageCode: settings.languageCode || 'en',
            }),
          });
          break;

        case 'vertex-ai':
          response = await fetch('/api/vertex-ai', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              prompt: input.trim(),
              model: settings.model,
              temperature: settings.temperature,
            }),
          });
          break;

        default:
          throw new Error('Invalid backend selected');
      }

      if (!response || !response.ok) {
        throw new Error('Failed to get response');
      }

      const data = await response.json();

      setMessages(prev => prev.map(msg =>
        msg.id === assistantMessage.id
          ? {
              ...msg,
              content: data.response || 'No response received',
              status: 'sent',
              isTyping: false,
              intent: data.intent,
              confidence: data.confidence,
            }
          : msg
      ));

      if (data.sessionId) {
        setSessionId(data.sessionId);
      }

    } catch (error) {
      setMessages(prev => prev.map(msg =>
        msg.id === assistantMessage.id
          ? {
              ...msg,
              content: `❌ Error: ${error instanceof Error ? error.message : 'Unknown error occurred'}`,
              status: 'error',
              isTyping: false,
            }
          : msg
      ));
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearChat = () => {
    setMessages([]);
    setSessionId(undefined);
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-white">
      {/* Enhanced Header with Gamification */}
      <div className="bg-white/90 backdrop-blur-xl border-b border-gray-200/50 px-6 py-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="relative">
              <div className={clsx(
                'w-12 h-12 rounded-2xl flex items-center justify-center shadow-lg',
                'bg-gradient-to-r from-purple-500 to-pink-500',
                'animate-gradient-shift'
              )}>
                <SparklesIcon className="w-6 h-6 text-white" />
              </div>
              {userStreak > 0 && (
                <div className="absolute -top-1 -right-1 w-6 h-6 bg-orange-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs font-bold">{userStreak}</span>
                </div>
              )}
            </div>

            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
                DaVita AI Playground
              </h1>
              <div className="flex items-center space-x-3 mt-1">
                <div className="flex items-center space-x-1">
                  <Trophy className="w-3 h-3 text-yellow-500" />
                  <span className="text-xs font-medium text-gray-600">Level {userLevel}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <Star className="w-3 h-3 text-purple-500" />
                  <span className="text-xs font-medium text-gray-600">{userXP} XP</span>
                </div>
                {userStreak >= 3 && (
                  <GamificationBadge type="streak" label={`${userStreak} Day Streak!`} />
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {/* IAP handles authentication - no client-side auth needed */}
            <div className="text-sm text-gray-600">
              <span className="font-medium">Authenticated via IAP</span>
            </div>

            {/* Memory Bank buttons (only for Agent Engine) */}
            {settings.backend === 'agent-engine' && (
              <div className="flex items-center space-x-2">
                {/* Save to Memory button */}
                {messages.length > 0 && (
                  <button
                    onClick={saveToMemoryBank}
                    disabled={savingToMemory}
                    className={clsx(
                      "flex items-center space-x-2 px-4 py-2 rounded-xl transition-all duration-300",
                      `bg-gradient-to-r ${memorySaved ? theme.colors.memory.success : theme.colors.memory.save} text-white`,
                      `hover:shadow-lg hover:scale-105 active:scale-95`,
                      savingToMemory && "opacity-50 cursor-not-allowed"
                    )}
                    title="Save conversation to Agent Memory Bank"
                  >
                    {savingToMemory ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : memorySaved ? (
                      <CheckCircle className="w-4 h-4" />
                    ) : (
                      <Brain className="w-4 h-4" />
                    )}
                    <span className="text-sm font-medium">
                      {savingToMemory ? 'Saving...' : memorySaved ? 'Saved!' : 'Save to Memory'}
                    </span>
                  </button>
                )}

                {/* Memory Browser button */}
                <button
                  onClick={() => setShowMemoryBrowser(!showMemoryBrowser)}
                  className={clsx(
                    "flex items-center space-x-2 px-4 py-2 rounded-xl transition-all duration-300",
                    `bg-gradient-to-r ${theme.colors.memory.browser} text-white`,
                    "hover:shadow-lg hover:scale-105 active:scale-95",
                    showMemoryBrowser && "ring-2 ring-white/30"
                  )}
                  title="Browse and search your memories"
                >
                  <Sparkles className="w-4 h-4" />
                  <span className="text-sm font-medium">Memory Browser</span>
                </button>
              </div>
            )}

            <button
              onClick={clearChat}
              className={clsx(
                "p-2.5 rounded-xl transition-all",
                "hover:bg-gray-100 hover:scale-110 active:scale-95"
              )}
              title="Clear chat"
            >
              <RefreshCw className="w-5 h-5 text-gray-600" />
            </button>

            {/* Theme Selector */}
            <div className="relative z-[60]">
              <button
                onClick={() => setShowThemeSelector(!showThemeSelector)}
                className={clsx(
                  "p-2.5 rounded-xl transition-all",
                  "hover:bg-gray-100 hover:scale-110 active:scale-95"
                )}
                title="Change Theme"
              >
                <Sparkles className="w-5 h-5 text-gray-600" />
              </button>
              
              {showThemeSelector && (
                <>
                  {/* Backdrop to close on click outside */}
                  <div 
                    className="fixed inset-0 z-[60]" 
                    onClick={() => setShowThemeSelector(false)}
                  />
                  <div className="absolute right-0 top-12 bg-white rounded-xl shadow-2xl border-2 border-gray-200 p-3 z-[70] w-48">
                    <p className="text-xs font-semibold text-gray-700 mb-2">Select Theme</p>
                    {getAvailableThemes().map((t) => (
                      <button
                        key={t.name}
                        onClick={() => {
                          setTheme(t.name);
                          setShowThemeSelector(false);
                        }}
                        className={clsx(
                          "w-full text-left px-3 py-2 rounded-lg transition-all mb-1",
                          theme.name === t.name
                            ? "bg-gradient-to-r " + t.colors.primary.gradient + " text-white font-medium"
                            : "hover:bg-gray-100 text-gray-700"
                        )}
                      >
                        {t.name === 'davita' ? '🏥 DaVita' : '🎨 Default'}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>

            <button
              onClick={() => setShowSettings(!showSettings)}
              className={clsx(
                "p-2.5 rounded-xl transition-all",
                "hover:bg-gray-100 hover:scale-110 active:scale-95"
              )}
              title="Settings"
            >
              <Settings className="w-5 h-5 text-gray-600" />
            </button>
          </div>
        </div>
      </div>

      {/* Instagram Stories-style Agent Selector */}
      {(settings.backend === 'agent-engine' && agents.length > 0) ||
       (settings.backend === 'dialogflow-cx' && dialogflowAgents.length > 0) ? (
        <div className="bg-white/80 backdrop-blur-sm border-b border-gray-200/50 px-6 py-4">
          <div className="flex items-center space-x-4 overflow-x-auto scrollbar-hide">
            <span className="text-sm font-semibold text-gray-700 whitespace-nowrap">
              Choose Agent:
            </span>
            {settings.backend === 'agent-engine'
              ? agents.map(agent => (
                  <AgentStoryBubble
                    key={agent.id}
                    agent={agent}
                    isActive={settings.agentId === agent.id}
                    onClick={() => setSettings(prev => ({ ...prev, agentId: agent.id }))}
                  />
                ))
              : dialogflowAgents.map(agent => (
                  <AgentStoryBubble
                    key={agent.id}
                    agent={agent}
                    isActive={settings.dialogflowAgentId === agent.id}
                    onClick={() => setSettings(prev => ({ ...prev, dialogflowAgentId: agent.id }))}
                  />
                ))
            }
          </div>
        </div>
      ) : null}

      {/* Settings Panel (Hidden by default) */}
      {showSettings && (
        <div className="bg-white/90 backdrop-blur-sm border-b border-gray-200/50 px-6 py-4 animate-slide-down">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Advanced Settings</h3>
            <button
              onClick={() => setShowSettings(false)}
              className="p-1 text-gray-400 hover:text-gray-600 rounded"
            >
              <XMarkIcon className="w-4 h-4" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Backend</label>
              <select
                value={settings.backend}
                onChange={(e) => setSettings(prev => ({ ...prev, backend: e.target.value as BackendType }))}
                className="w-full rounded-xl border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500"
              >
                <option value="agent-engine">🤖 Agent Engine</option>
                <option value="dialogflow-cx">💬 Dialogflow CX</option>
                <option value="vertex-ai">✨ Vertex AI</option>
              </select>
            </div>

            {settings.backend === 'agent-engine' && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Agent
                    {loadingAgents && <span className="text-xs text-gray-500 ml-1">(Loading...)</span>}
                  </label>
                  <button
                    onClick={fetchAgents}
                    disabled={loadingAgents}
                    className="p-1 text-gray-400 hover:text-gray-600 rounded transition-colors"
                    title="Refresh agents"
                  >
                    <RefreshCw className={clsx('w-3 h-3', loadingAgents && 'animate-spin')} />
                  </button>
                </div>
                {loadingAgents ? (
                  <div className="w-full h-10 bg-gray-100 animate-pulse rounded-lg"></div>
                ) : (
                  <select
                    value={settings.agentId || ''}
                    onChange={(e) => setSettings(prev => ({ ...prev, agentId: e.target.value }))}
                    className="w-full rounded-xl border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500 transition-colors"
                    disabled={agents.length === 0}
                  >
                    <option value="">Select an agent</option>
                    {agents.map((agent) => (
                      <option key={agent.id} value={agent.id}>
                        {agent.display_name}
                        {agent.state !== 'ACTIVE' && agent.state && ` (${agent.state})`}
                        {agent.display_name.toLowerCase().includes('demo') && !agent.display_name.toLowerCase().includes('adk') && ' ⭐ Recommended'}
                      </option>
                    ))}
                  </select>
                )}
                {agents.length === 0 && !loadingAgents && (
                  <p className="text-xs text-red-500 mt-1">No agents found</p>
                )}
                {settings.agentId && agents.find(a => a.id === settings.agentId)?.display_name?.toLowerCase().includes('adk') && (
                  <p className="text-xs text-amber-600 mt-1">
                    ⚠️ ADK agents may have limited conversation support. Try &quot;Demo Agent&quot; if you encounter issues.
                  </p>
                )}
              </div>
            )}

            {/* Streaming toggle for Agent Engine */}
            {settings.backend === 'agent-engine' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Performance Options
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="enableStreaming"
                    checked={settings.enableStreaming !== false}
                    onChange={(e) => setSettings(prev => ({ ...prev, enableStreaming: e.target.checked }))}
                    className="rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                  />
                  <label htmlFor="enableStreaming" className="text-sm text-gray-600">
                    Enable streaming responses (faster)
                  </label>
                </div>
              </div>
            )}

            {settings.backend === 'dialogflow-cx' && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Dialogflow Agent
                    {loadingDialogflowAgents && <span className="text-xs text-gray-500 ml-1">(Loading...)</span>}
                  </label>
                  <button
                    onClick={fetchDialogflowAgents}
                    disabled={loadingDialogflowAgents}
                    className="p-1 text-gray-400 hover:text-gray-600 rounded transition-colors"
                    title="Refresh Dialogflow agents"
                  >
                    <RefreshCw className={clsx('w-3 h-3', loadingDialogflowAgents && 'animate-spin')} />
                  </button>
                </div>
                {loadingDialogflowAgents ? (
                  <div className="w-full h-10 bg-gray-100 animate-pulse rounded-lg"></div>
                ) : (
                  <select
                    value={settings.dialogflowAgentId || ''}
                    onChange={(e) => setSettings(prev => ({ ...prev, dialogflowAgentId: e.target.value }))}
                    className="w-full rounded-xl border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500 transition-colors"
                    disabled={dialogflowAgents.length === 0}
                  >
                    <option value="">Select a Dialogflow agent</option>
                    {dialogflowAgents.map((agent) => (
                      <option key={agent.id} value={agent.id}>
                        {agent.display_name}
                      </option>
                    ))}
                  </select>
                )}
                {dialogflowAgents.length === 0 && !loadingDialogflowAgents && (
                  <p className="text-xs text-red-500 mt-1">No Dialogflow agents found</p>
                )}
              </div>
            )}

            {settings.backend === 'vertex-ai' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Model</label>
                  <select
                    value={settings.model || 'gemini-2.0-flash'}
                    onChange={(e) => setSettings(prev => ({ ...prev, model: e.target.value }))}
                    className="w-full rounded-xl border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500"
                  >
                    <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                    <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
                    <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Temperature: {settings.temperature}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="2"
                    step="0.1"
                    value={settings.temperature || 0.7}
                    onChange={(e) => setSettings(prev => ({ ...prev, temperature: parseFloat(e.target.value) }))}
                    className="w-full h-2 bg-gradient-to-r from-blue-200 to-purple-200 rounded-lg appearance-none cursor-pointer"
                  />
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Messages Area with Enhanced Styling */}
      <div className="flex-1 overflow-y-auto px-6 py-6 scrollbar-thin scrollbar-thumb-purple-300">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.length === 0 && (
            <div className="text-center py-16">
              <div className={clsx(
                "w-20 h-20 mx-auto mb-6 rounded-3xl flex items-center justify-center",
                "bg-gradient-to-br from-purple-500 to-pink-500 shadow-2xl",
                "animate-float"
              )}>
                <Rocket className="w-10 h-10 text-white" />
              </div>
              <h3 className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent mb-3">
                Ready to Chat?
              </h3>
              <p className="text-gray-600 mb-8">Start a conversation with your AI companion</p>

              {/* Quick action suggestions */}
              <div className="flex flex-wrap justify-center gap-3">
                {[
                  { icon: Sparkles, text: "What can you help me with?", color: "from-purple-500 to-pink-500" },
                  { icon: Target, text: "Help me learn", color: "from-blue-500 to-purple-500" },
                  { icon: Brain, text: "Remember this", color: "from-pink-500 to-orange-500" },
                ].map((suggestion, idx) => (
                  <button
                    key={idx}
                    onClick={() => setInput(suggestion.text)}
                    className={clsx(
                      "group flex items-center space-x-2 px-5 py-3 rounded-full",
                      "bg-white border-2 border-gray-200",
                      "hover:border-transparent hover:shadow-lg",
                      "transform transition-all hover:scale-105 active:scale-95"
                    )}
                  >
                    <div className={clsx(
                      "w-8 h-8 rounded-full flex items-center justify-center",
                      "bg-gradient-to-r", suggestion.color,
                      "group-hover:animate-pulse"
                    )}>
                      <suggestion.icon className="w-4 h-4 text-white" />
                    </div>
                    <span className="text-sm font-medium text-gray-700">{suggestion.text}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              onCopy={copyToClipboard}
            />
          ))}
        </div>
        <div ref={messagesEndRef} />
      </div>

      {/* Enhanced Input Area */}
      <div className="bg-white/90 backdrop-blur-xl border-t border-gray-200/50 px-6 py-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-end space-x-3">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type your message..."
                className={clsx(
                  "w-full rounded-2xl border-2 border-gray-200",
                  "focus:border-purple-500 focus:ring-4 focus:ring-purple-500/20",
                  "resize-none px-5 py-3 pr-12",
                  "transition-all duration-200",
                  "min-h-[52px] max-h-[120px]",
                  "placeholder-gray-400"
                )}
                rows={1}
                disabled={isLoading}
              />

              {/* Voice input button */}
              <button
                onClick={() => setIsListening(!isListening)}
                className={clsx(
                  "absolute right-3 bottom-3 p-2 rounded-full transition-all",
                  isListening
                    ? "bg-red-100 text-red-600 animate-pulse"
                    : "text-gray-400 hover:text-gray-600 hover:bg-gray-100"
                )}
              >
                {isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
              </button>
            </div>

            {/* Send button */}
            <button
              onClick={sendMessage}
              disabled={!input.trim() || isLoading}
              className={clsx(
                "p-3.5 rounded-2xl transition-all duration-200",
                "shadow-lg hover:shadow-xl",
                "transform hover:scale-105 active:scale-95",
                !input.trim() || isLoading
                  ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                  : `bg-gradient-to-r ${theme.colors.primary.gradient} text-white`
              )}
            >
              {isLoading ? (
                <RefreshCw className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>

          {/* Character count and hints */}
          <div className="flex items-center justify-between mt-2 px-2">
            <span className="text-xs text-gray-400">
              {input.length > 0 && `${input.length} characters`}
            </span>
            <span className="text-xs text-gray-400">
              Press Enter to send, Shift+Enter for new line
            </span>
          </div>
        </div>
      </div>

      {/* Memory Browser Modal */}
      {showMemoryBrowser && settings.backend === 'agent-engine' && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200"
          onClick={() => setShowMemoryBrowser(false)}
        >
          <div 
            className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[80vh] flex flex-col animate-in slide-in-from-bottom duration-300"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className={clsx(
              "flex items-center justify-between p-6 border-b border-gray-200",
              theme.name === 'davita' ? "bg-gradient-to-r from-orange-50 to-cyan-50" : "bg-gradient-to-r from-indigo-50 to-purple-50"
            )}>
              <div className="flex items-center space-x-3">
                <div className={`p-3 bg-gradient-to-r ${theme.colors.secondary.gradient} rounded-xl shadow-lg`}>
                  <Brain className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">Memory Browser</h2>
                  <p className="text-sm text-gray-600">Search and explore your saved conversations</p>
                </div>
              </div>
              <button
                onClick={() => setShowMemoryBrowser(false)}
                className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
              >
                <XMarkIcon className="w-6 h-6 text-gray-600" />
              </button>
            </div>

            {/* Search Bar */}
            <div className="p-6 border-b border-gray-200">
              <div className="flex space-x-3">
                <input
                  type="text"
                  value={memorySearchQuery}
                  onChange={(e) => setMemorySearchQuery(e.target.value)}
                  placeholder="Search your memories... (e.g., 'conversations about authentication')"
                  className="flex-1 px-4 py-3 border-2 border-gray-300 rounded-xl focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all"
                  onKeyPress={(e) => {
                    if (e.key === 'Enter' && memorySearchQuery.trim()) {
                      searchMemories(memorySearchQuery);
                    }
                  }}
                />
                <button
                  onClick={() => searchMemories(memorySearchQuery)}
                  disabled={searchingMemories || !memorySearchQuery.trim()}
                  className={clsx(
                    "px-6 py-3 rounded-xl transition-all duration-300",
                    `bg-gradient-to-r ${theme.colors.secondary.gradient} text-white`,
                    "hover:shadow-lg hover:scale-105 active:scale-95",
                    "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                  )}
                >
                  {searchingMemories ? (
                    <RefreshCw className="w-5 h-5 animate-spin" />
                  ) : (
                    <span className="font-medium">Search</span>
                  )}
                </button>
              </div>
            </div>

            {/* Results */}
            <div className="flex-1 overflow-y-auto p-6">
              {searchingMemories ? (
                <div className="flex flex-col items-center justify-center h-full space-y-4">
                  <RefreshCw className="w-12 h-12 text-indigo-500 animate-spin" />
                  <p className="text-gray-600">Searching memories...</p>
                </div>
              ) : memories.length > 0 ? (
                <div className="space-y-4">
                  <p className="text-sm text-gray-600 mb-3">Found {memories.length} memory/memories</p>
                  {memories.map((memory, index) => {
                    // ADK memory structure might vary, handle different formats
                    const memoryData = memory.memory || memory;
                    
                    // Extract text content from nested structure
                    let content = '';
                    if (typeof memoryData.content === 'object' && memoryData.content?.parts?.[0]?.text) {
                      // Nested ADK structure: memory.content.parts[0].text
                      content = memoryData.content.parts[0].text;
                    } else if (memoryData.content && typeof memoryData.content === 'string') {
                      content = memoryData.content;
                    } else if (memoryData.text) {
                      content = memoryData.text;
                    } else if (memoryData.summary) {
                      content = memoryData.summary;
                    } else {
                      content = JSON.stringify(memoryData, null, 2);
                    }
                    
                    // Get author info
                    const author = memoryData.author || 'Unknown';
                    
                    // Theme-aware card styling
                    const cardBg = theme.name === 'davita' 
                      ? 'from-orange-50 to-cyan-50' 
                      : 'from-indigo-50 to-purple-50';
                    const cardBorder = theme.name === 'davita'
                      ? 'border-orange-100 hover:border-orange-300'
                      : 'border-indigo-100 hover:border-indigo-300';
                    
                    return (
                      <div
                        key={index}
                        className={clsx(
                          "p-5 rounded-xl border-2 transition-all duration-200 hover:shadow-lg",
                          `bg-gradient-to-r ${cardBg} ${cardBorder}`
                        )}
                      >
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center space-x-2">
                            <Sparkles className={clsx(
                              "w-5 h-5",
                              theme.name === 'davita' ? "text-orange-500" : "text-indigo-500"
                            )} />
                            <h3 className="font-semibold text-gray-900">
                              {memoryData.title || (author === 'user' ? '💬 User Message' : '🤖 Agent Response')}
                            </h3>
                          </div>
                          <span className="text-xs text-gray-500 bg-white px-2 py-1 rounded-full">
                            {memoryData.timestamp || memoryData.created_at
                              ? new Date(memoryData.timestamp || memoryData.created_at || 0).toLocaleDateString()
                              : 'Recent'}
                          </span>
                        </div>
                        <div className="text-sm text-gray-500 mb-2">
                          {author === 'user' ? '👤 User' : author === 'agent' ? '🤖 Agent' : `📝 ${author}`}
                        </div>
                        <p className="text-gray-700 leading-relaxed mb-3 whitespace-pre-wrap">
                          {content}
                        </p>
                        
                        {/* Action button */}
                        <div className="flex items-center space-x-2 mt-3 pt-3 border-t border-gray-200">
                          <button
                            onClick={() => loadMemory(memory)}
                            className={clsx(
                              "flex items-center space-x-1 px-3 py-1.5 rounded-lg transition-all",
                              `bg-gradient-to-r ${theme.colors.secondary.gradient} text-white text-sm font-medium`,
                              "hover:shadow-md hover:scale-105 active:scale-95"
                            )}
                            title="Load this memory into the current conversation"
                          >
                            <Sparkles className="w-3.5 h-3.5" />
                            <span>Load to Chat</span>
                          </button>
                        </div>
                        
                        {(memoryData.relevance_score || memoryData.score) && (
                          <div className="flex items-center space-x-2">
                            <div className="flex-1 bg-gray-200 rounded-full h-2">
                              <div
                                className={`bg-gradient-to-r ${theme.colors.secondary.gradient} h-2 rounded-full transition-all duration-500`}
                                style={{ width: `${((memoryData.relevance_score || memoryData.score || 0) * 100)}%` }}
                              />
                            </div>
                            <span className="text-xs text-gray-600 font-medium">
                              {Math.round((memoryData.relevance_score || memoryData.score || 0) * 100)}% match
                            </span>
                          </div>
                        )}
                        {/* Debug info in development */}
                        {process.env.NODE_ENV === 'development' && (
                          <details className="mt-2">
                            <summary className="text-xs text-gray-400 cursor-pointer">Debug Info</summary>
                            <pre className="text-xs text-gray-500 mt-2 overflow-auto">
                              {JSON.stringify(memory, null, 2)}
                            </pre>
                          </details>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : memorySearchQuery ? (
                <div className="flex flex-col items-center justify-center h-full space-y-4 text-center">
                  <div className="p-4 bg-gray-100 rounded-full">
                    <Brain className="w-12 h-12 text-gray-400" />
                  </div>
                  <div>
                    <p className="text-lg font-semibold text-gray-900">No memories found</p>
                    <p className="text-gray-600 mt-2">
                      Try a different search query or save your current conversation to create a new memory.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full space-y-4 text-center">
                  <div className="p-4 bg-gradient-to-r from-indigo-100 to-purple-100 rounded-full">
                    <Sparkles className="w-12 h-12 text-indigo-500" />
                  </div>
                  <div>
                    <p className="text-lg font-semibold text-gray-900">Search Your Memories</p>
                    <p className="text-gray-600 mt-2 max-w-md">
                      Enter a search query to find relevant conversations you&apos;ve saved to the memory bank.
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-gray-200 bg-gray-50 rounded-b-2xl">
              <p className="text-xs text-gray-500 text-center">
                💡 Tip: Save conversations with the &quot;Save to Memory&quot; button to build your memory bank
              </p>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}