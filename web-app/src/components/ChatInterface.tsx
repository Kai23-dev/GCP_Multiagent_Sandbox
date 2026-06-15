'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { SparklesIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { Bot, User, Settings, Send, Zap, Clock, CheckCircle, AlertCircle, Copy, RefreshCw, Mic, MicOff } from 'lucide-react';
import clsx from 'clsx';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import 'highlight.js/styles/github-dark.css'; // You can change this theme
import { useConfig } from '@/hooks/useConfig';

// Types for ReactMarkdown components
type CodeProps = React.HTMLAttributes<HTMLElement> & {
  inline?: boolean;
  children?: React.ReactNode;
};

type PreProps = React.HTMLAttributes<HTMLPreElement> & {
  children?: React.ReactNode;
};

type BackendType = 'agent-engine' | 'dialogflow-cx' | 'vertex-ai';

interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  backend?: BackendType;
  status?: 'sending' | 'sent' | 'error';
  intent?: string;
  confidence?: number;
}

interface ChatSettings {
  backend: BackendType;
  agentId?: string;
  dialogflowAgentId?: string;
  dataStoreId?: string;
  model?: string;
  temperature?: number;
  languageCode?: string;
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

const TypingIndicator = () => (
  <div className="flex items-center space-x-2 px-4 py-3 bg-white rounded-2xl shadow-sm border border-gray-100 max-w-20">
    <div className="flex space-x-1">
      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
    </div>
  </div>
);

const MessageBubble = ({ message, onCopy }: { message: Message; onCopy: (content: string) => void }) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    onCopy(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={clsx(
      'flex items-start space-x-3 group animate-fade-in',
      isUser ? 'justify-end' : 'justify-start'
    )}>
      {!isUser && (
        <div className="flex-shrink-0">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center shadow-lg">
            <Bot className="w-4 h-4 text-white" />
          </div>
        </div>
      )}
      
      <div className={clsx(
        'max-w-sm lg:max-w-3xl px-6 py-4 rounded-2xl shadow-sm relative',
        isUser 
          ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-br-md' 
          : 'bg-white border border-gray-100 text-gray-800 rounded-bl-md'
      )}>
        <div className="break-words markdown-content">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeHighlight, rehypeRaw]}
            components={{
              // Custom styling for inline code - keep it truly inline
              code: ({ inline, className, children, ...props }: CodeProps) => {
                if (inline) {
                  return (
                    <code
                      className={clsx(
                        'inline-code',
                        'px-1.5 py-0.5 rounded text-sm font-mono',
                        isUser 
                          ? 'bg-white/20 text-blue-100 border border-white/30' 
                          : 'bg-yellow-100 text-amber-800 border border-yellow-300'
                      )}
                      {...props}
                    >
                      {children}
                    </code>
                  );
                }
                return (
                  <code
                    className={clsx(
                      'block p-3 rounded-md text-sm font-mono overflow-x-auto',
                      'bg-gray-900 text-gray-100',
                      className
                    )}
                    {...props}
                  >
                    {children}
                  </code>
                );
              },
              // Custom styling for pre blocks
              pre: ({ children, ...props }: PreProps) => (
                <pre
                  className="rounded-md overflow-x-auto my-2"
                  {...props}
                >
                  {children}
                </pre>
              ),
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>
        
        {/* Message status and timestamp */}
        <div className={clsx(
          'flex items-center justify-between mt-2 text-xs',
          isUser ? 'text-blue-100' : 'text-gray-500'
        )}>
          <div className="flex items-center space-x-1">
            <Clock className="w-3 h-3" />
            <span>{message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            {message.backend && (
              <span className="ml-2 px-2 py-0.5 bg-black/10 rounded-full text-xs">
                {message.backend === 'agent-engine' ? 'Agent' : 
                 message.backend === 'dialogflow-cx' ? 'Dialogflow' : 'AI'}
              </span>
            )}
            {message.intent && (
              <span className="ml-2 px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs">
                Intent: {message.intent} {message.confidence && `(${Math.round(message.confidence * 100)}%)`}
              </span>
            )}
          </div>
          
          {isUser && message.status && (
            <div className="flex items-center">
              {message.status === 'sending' && <Clock className="w-3 h-3 animate-spin" />}
              {message.status === 'sent' && <CheckCircle className="w-3 h-3" />}
              {message.status === 'error' && <AlertCircle className="w-3 h-3 text-red-300" />}
            </div>
          )}
        </div>

        {/* Copy button */}
        <button
          onClick={handleCopy}
          className={clsx(
            'absolute top-2 right-2 p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity',
            isUser ? 'hover:bg-white/20' : 'hover:bg-gray-100'
          )}
        >
          {copied ? (
            <CheckCircle className="w-3 h-3 text-green-500" />
          ) : (
            <Copy className={clsx('w-3 h-3', isUser ? 'text-white/70' : 'text-gray-400')} />
          )}
        </button>
      </div>

      {isUser && (
        <div className="flex-shrink-0">
          <div className="w-8 h-8 bg-gradient-to-br from-gray-600 to-gray-700 rounded-full flex items-center justify-center shadow-lg">
            <User className="w-4 h-4 text-white" />
          </div>
        </div>
      )}
    </div>
  );
};

export default function ChatInterface() {
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
  const [agentsCacheInfo, setAgentsCacheInfo] = useState<{
    cached: boolean;
    stale?: boolean;
    cacheAge?: number;
    refreshed?: boolean;
  } | null>(null);
  const [dialogflowAgentsCacheInfo, setDialogflowAgentsCacheInfo] = useState<{
    cached: boolean;
    stale?: boolean;
    cacheAge?: number;
    refreshed?: boolean;
  } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  
  // Get runtime configuration (for project info, environment flags)
  const { config } = useConfig();
  console.log('Runtime config:', config); // Used for debugging environment
  
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

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const fetchAgents = useCallback(async () => {
    setLoadingAgents(true);
    try {
      const response = await fetch('/api/agents');
      if (!response.ok) {
        throw new Error('Failed to fetch agents');
      }
      const data = await response.json();
      if (data.success && data.agents) {
        setAgents(data.agents);
        setAgentsCacheInfo({
          cached: data.cached || false,
          stale: data.stale || false,
          cacheAge: data.cacheAge,
          refreshed: data.refreshed || false,
        });
        
        // Auto-select the first agent if none is selected
        if (!settings.agentId && data.agents.length > 0) {
          setSettings(prev => ({ ...prev, agentId: data.agents[0].id }));
        }
      }
    } catch (error) {
      console.error('Error fetching agents:', error);
      setAgentsCacheInfo(null);
    } finally {
      setLoadingAgents(false);
    }
  }, [settings.agentId]);

  const refreshAgents = async () => {
    setLoadingAgents(true);
    try {
      const response = await fetch('/api/agents', { method: 'POST' });
      if (!response.ok) {
        throw new Error('Failed to refresh agents');
      }
      const data = await response.json();
      if (data.success && data.agents) {
        setAgents(data.agents);
        setAgentsCacheInfo({
          cached: false,
          refreshed: true,
        });
        
        // Auto-select the first agent if none is selected
        if (!settings.agentId && data.agents.length > 0) {
          setSettings(prev => ({ ...prev, agentId: data.agents[0].id }));
        }
      }
    } catch (error) {
      console.error('Error refreshing agents:', error);
    } finally {
      setLoadingAgents(false);
    }
  };

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
        setDialogflowAgentsCacheInfo({
          cached: data.cached || false,
          stale: data.stale || false,
          cacheAge: data.cacheAge,
          refreshed: data.refreshed || false,
        });
        
        // Auto-select the first agent if none is selected
        if (!settings.dialogflowAgentId && data.agents.length > 0) {
          setSettings(prev => ({ ...prev, dialogflowAgentId: data.agents[0].id }));
        }
      }
    } catch (error) {
      console.error('Error fetching Dialogflow agents:', error);
      setDialogflowAgentsCacheInfo(null);
    } finally {
      setLoadingDialogflowAgents(false);
    }
  }, [settings.dialogflowAgentId]);

  const refreshDialogflowAgents = async () => {
    setLoadingDialogflowAgents(true);
    try {
      const response = await fetch('/api/dialogflow-agents', { method: 'POST' });
      if (!response.ok) {
        throw new Error('Failed to refresh Dialogflow agents');
      }
      const data = await response.json();
      if (data.success && data.agents) {
        setDialogflowAgents(data.agents);
        setDialogflowAgentsCacheInfo({
          cached: false,
          refreshed: true,
        });
        
        // Auto-select the first agent if none is selected
        if (!settings.dialogflowAgentId && data.agents.length > 0) {
          setSettings(prev => ({ ...prev, dialogflowAgentId: data.agents[0].id }));
        }
      }
    } catch (error) {
      console.error('Error refreshing Dialogflow agents:', error);
    } finally {
      setLoadingDialogflowAgents(false);
    }
  };

  // Fetch agents when component mounts or when backend changes to agent-engine
  useEffect(() => {
    if (settings.backend === 'agent-engine') {
      fetchAgents();
    } else if (settings.backend === 'dialogflow-cx') {
      fetchDialogflowAgents();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings.backend]); // Remove fetchAgents and fetchDialogflowAgents from deps to avoid infinite loop

  // Clear chat history when backend type changes
  useEffect(() => {
    if (messages.length > 0) {
      setMessages([]);
      setSessionId(undefined);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings.backend]); // Remove messages.length from deps to avoid infinite loop

  // Clear chat history when agent changes (for agent-engine backend)
  useEffect(() => {
    if (settings.backend === 'agent-engine' && messages.length > 0) {
      setMessages([]);
      setSessionId(undefined);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings.agentId, settings.backend]); // Remove messages.length from deps to avoid infinite loop

  // Clear chat history when Dialogflow agent changes
  useEffect(() => {
    if (settings.backend === 'dialogflow-cx' && messages.length > 0) {
      setMessages([]);
      setSessionId(undefined);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings.dialogflowAgentId, settings.backend]); // Remove messages.length from deps to avoid infinite loop

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const messageContent = input.trim(); // Store the message content before clearing
    const userMessage: Message = {
      id: Date.now().toString(),
      content: messageContent,
      role: 'user',
      timestamp: new Date(),
      status: 'sending',
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    // Update message status to sent
    setTimeout(() => {
      setMessages(prev => prev.map(msg => 
        msg.id === userMessage.id ? { ...msg, status: 'sent' } : msg
      ));
    }, 500);

    try {
      let response;
      
      switch (settings.backend) {
        case 'agent-engine':
          if (!settings.agentId) {
            throw new Error('Please select an agent first');
          }
          response = await fetch('/api/agent-engine', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              message: messageContent,
              agentId: settings.agentId,
              sessionId,
            }),
          });
          break;

        case 'dialogflow-cx':
          if (!settings.dialogflowAgentId) {
            throw new Error('Please select a Dialogflow agent first');
          }
          response = await fetch('/api/dialogflow-cx', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              message: messageContent,
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
              prompt: messageContent,
              model: settings.model,
              temperature: settings.temperature,
            }),
          });
          break;

        default:
          throw new Error('Invalid backend selected');
      }

      if (!response.ok) {
        let errorMessage = 'Failed to get response';
        try {
          const errorData = await response.json();
          errorMessage = errorData.error || errorMessage;
        } catch {
          // If we can't parse JSON, the server likely returned HTML
          const textResponse = await response.text();
          console.error('Server returned non-JSON response:', textResponse);
          errorMessage = `Server error (${response.status}): ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      let data;
      try {
        data = await response.json();
      } catch (parseError) {
        console.error('Failed to parse JSON response:', parseError);
        throw new Error('Server returned invalid JSON response. Check browser console for details.');
      }
      
      let assistantContent = '';
      let intent = undefined;
      let confidence = undefined;
      
      if (settings.backend === 'dialogflow-cx') {
        assistantContent = data.response || 'No response received';
        intent = data.intent;
        confidence = data.intentDetectionConfidence;
      } else {
        assistantContent = data.response || 'No response received';
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: assistantContent,
        role: 'assistant',
        timestamp: new Date(),
        backend: settings.backend,
        intent,
        confidence,
      };

      setMessages(prev => [...prev, assistantMessage]);
      
      if (data.sessionId) {
        setSessionId(data.sessionId);
      }

    } catch (error) {
      // Update user message status to error
      setMessages(prev => prev.map(msg => 
        msg.id === userMessage.id ? { ...msg, status: 'error' } : msg
      ));

      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `❌ Error: ${error instanceof Error ? error.message : 'Unknown error occurred'}`,
        role: 'assistant',
        timestamp: new Date(),
        backend: settings.backend,
      };
      setMessages(prev => [...prev, errorMessage]);
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
  };

  const getBackendColor = (backend: BackendType) => {
    switch (backend) {
      case 'agent-engine': return 'from-blue-500 to-blue-600';
      case 'dialogflow-cx': return 'from-green-500 to-green-600';
      case 'vertex-ai': return 'from-purple-500 to-purple-600';
      default: return 'from-gray-500 to-gray-600';
    }
  };

  const getBackendName = (backend: BackendType) => {
    switch (backend) {
      case 'agent-engine': return 'Agent Engine';
      case 'dialogflow-cx': return 'Dialogflow CX';
      case 'vertex-ai': return 'Vertex AI';
    default: return 'Unknown';
  }
};

const getSelectedAgentName = () => {
  if (settings.backend === 'agent-engine' && settings.agentId) {
    const selectedAgent = agents.find(agent => agent.id === settings.agentId);
    return selectedAgent ? selectedAgent.display_name : 'Unknown Agent';
  } else if (settings.backend === 'dialogflow-cx' && settings.dialogflowAgentId) {
    const selectedAgent = dialogflowAgents.find(agent => agent.id === settings.dialogflowAgentId);
    return selectedAgent ? selectedAgent.display_name : 'Unknown Dialogflow Agent';
  }
  return getBackendName(settings.backend);
};  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <div className="bg-white/80 backdrop-blur-sm border-b border-gray-200/50 px-6 py-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className={clsx(
              'w-10 h-10 rounded-full flex items-center justify-center shadow-lg bg-gradient-to-r',
              getBackendColor(settings.backend)
            )}>
              <SparklesIcon className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">DaVita Agent Marketplace</h1>
              <p className="text-sm text-gray-500 flex items-center space-x-2">
                <Zap className="w-3 h-3" />
                <span>Powered by {getSelectedAgentName()}</span>
                {sessionId && (
                  <span className="ml-2 px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-xs">
                    Session Active
                  </span>
                )}
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            {/* IAP handles authentication - no client-side auth needed */}
            <div className="text-xs text-gray-500">
              <span>Authenticated via IAP</span>
            </div>
            
            <button
              onClick={clearChat}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"
              title="Clear chat"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"
              title="Settings"
            >
              <Settings className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="bg-white/90 backdrop-blur-sm border-b border-gray-200/50 px-6 py-4 animate-slide-down">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Settings</h3>
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
                className="w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 transition-colors"
              >
                <option value="agent-engine">🤖 Agent Engine</option>
                <option value="dialogflow-cx">� Dialogflow CX</option>
                <option value="vertex-ai">✨ Vertex AI</option>
              </select>
            </div>

            {settings.backend === 'agent-engine' && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Agent 
                    {loadingAgents && <span className="text-xs text-gray-500 ml-1">(Loading...)</span>}
                    {agentsCacheInfo?.cached && !loadingAgents && (
                      <span className={clsx('text-xs ml-1', agentsCacheInfo.stale ? 'text-orange-500' : 'text-green-600')}>
                        ({agentsCacheInfo.stale ? 'Cached - updating...' : 'Cached'})
                      </span>
                    )}
                  </label>
                  <button
                    onClick={refreshAgents}
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
                    className="w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 transition-colors"
                    disabled={agents.length === 0}
                  >
                    <option value="">Select an agent</option>
                    {agents.map((agent) => (
                      <option key={agent.id} value={agent.id}>
                        {agent.display_name} {agent.state !== 'ACTIVE' && agent.state && `(${agent.state})`}
                      </option>
                    ))}
                  </select>
                )}
                {agents.length === 0 && !loadingAgents && (
                  <p className="text-xs text-red-500 mt-1">No agents with display names found</p>
                )}
                {agentsCacheInfo?.refreshed && (
                  <p className="text-xs text-green-600 mt-1">✓ Agents refreshed</p>
                )}
              </div>
            )}

            {settings.backend === 'dialogflow-cx' && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Dialogflow Agent 
                    {loadingDialogflowAgents && <span className="text-xs text-gray-500 ml-1">(Loading...)</span>}
                    {dialogflowAgentsCacheInfo?.cached && !loadingDialogflowAgents && (
                      <span className={clsx('text-xs ml-1', dialogflowAgentsCacheInfo.stale ? 'text-orange-500' : 'text-green-600')}>
                        ({dialogflowAgentsCacheInfo.stale ? 'Cached - updating...' : 'Cached'})
                      </span>
                    )}
                  </label>
                  <button
                    onClick={refreshDialogflowAgents}
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
                    className="w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 transition-colors"
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
                {dialogflowAgentsCacheInfo?.refreshed && (
                  <p className="text-xs text-green-600 mt-1">✓ Dialogflow agents refreshed</p>
                )}
              </div>
            )}
{/* 
            {settings.backend === 'dialogflow-cx' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Language Code</label>
                <select
                  value={settings.languageCode || 'en'}
                  onChange={(e) => setSettings(prev => ({ ...prev, languageCode: e.target.value }))}
                  className="w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 transition-colors"
                >
                  <option value="en">English (en)</option>
                  <option value="es">Spanish (es)</option>
                  <option value="fr">French (fr)</option>
                  <option value="de">German (de)</option>
                  <option value="it">Italian (it)</option>
                  <option value="pt">Portuguese (pt)</option>
                  <option value="ru">Russian (ru)</option>
                  <option value="ja">Japanese (ja)</option>
                  <option value="ko">Korean (ko)</option>
                  <option value="zh">Chinese (zh)</option>
                </select>
              </div>
            )} */}

            {settings.backend === 'vertex-ai' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Model</label>
                  <select
                    value={settings.model || 'gemini-2.0-flash'}
                    onChange={(e) => setSettings(prev => ({ ...prev, model: e.target.value }))}
                    className="w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 transition-colors"
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
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
                  />
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.length === 0 && (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg">
                <SparklesIcon className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Welcome to DaVita Agent Marketplace</h3>
              {(settings.backend === 'agent-engine' && !settings.agentId) || 
               (settings.backend === 'dialogflow-cx' && !settings.dialogflowAgentId) ? (
                <p className="text-gray-600 mb-6">Please select an agent from the settings to start chatting</p>
              ) : (
                <>
                  <p className="text-gray-600 mb-6">Start a conversation with your AI assistant</p>
                  <div className="flex flex-wrap justify-center gap-2">
                    <button
                      onClick={() => setInput("What can you help me with?")}
                      className="px-4 py-2 bg-blue-50 text-blue-700 rounded-full text-sm hover:bg-blue-100 transition-colors"
                    >
                      What can you help me with?
                    </button>
                    {/* <button
                      onClick={() => setInput("What can you do?")}
                      className="px-4 py-2 bg-purple-50 text-purple-700 rounded-full text-sm hover:bg-purple-100 transition-colors"
                    >
                      Time in New York
                    </button> */}
                  </div>
                </>
              )}
            </div>
          )}

          {messages.map((message) => (
            <MessageBubble 
              key={message.id} 
              message={message} 
              onCopy={copyToClipboard}
            />
          ))}
          
          {isLoading && (
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center shadow-lg">
                  <Bot className="w-4 h-4 text-white" />
                </div>
              </div>
              <TypingIndicator />
            </div>
          )}
        </div>
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="bg-white/80 backdrop-blur-sm border-t border-gray-200/50 px-6 py-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-end space-x-4">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type your message..."
                className="w-full rounded-2xl border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 resize-none px-4 py-3 pr-12 transition-all duration-200 min-h-[48px] max-h-[120px]"
                rows={1}
                disabled={isLoading}
              />
              <div className="absolute right-3 bottom-3 flex items-center space-x-1">
                <button
                  onClick={() => setIsListening(!isListening)}
                  className={clsx(
                    'p-1.5 rounded-full transition-colors',
                    isListening 
                      ? 'bg-red-100 text-red-600 hover:bg-red-200' 
                      : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
                  )}
                  title={isListening ? 'Stop listening' : 'Start voice input'}
                >
                  {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <button
              onClick={sendMessage}
              disabled={!input.trim() || isLoading || 
                       (settings.backend === 'agent-engine' && !settings.agentId) ||
                       (settings.backend === 'dialogflow-cx' && !settings.dialogflowAgentId)}
              className={clsx(
                'p-3 rounded-2xl transition-all duration-200 shadow-lg',
                !input.trim() || isLoading || 
                (settings.backend === 'agent-engine' && !settings.agentId) ||
                (settings.backend === 'dialogflow-cx' && !settings.dialogflowAgentId)
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-gradient-to-r from-blue-600 to-blue-700 text-white hover:from-blue-700 hover:to-blue-800 hover:shadow-xl transform hover:scale-105'
              )}
            >
              {isLoading ? (
                <RefreshCw className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}