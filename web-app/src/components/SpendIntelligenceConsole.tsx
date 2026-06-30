"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  Send, Copy, CheckCircle, Clock, ChevronRight,
  AlertCircle, RefreshCw, Bot, User, Menu, X,
  BarChart2, TrendingUp, Shield, Search, Users,
  FileText, Activity, Database, Layers,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";
import "highlight.js/styles/github.css";

/* ─── Types ──────────────────────────────────────────────────────────────── */

interface Message {
  id: string;
  content: string;
  role: "user" | "assistant";
  timestamp: Date;
  status?: "sending" | "sent" | "error" | "streaming";
  isTyping?: boolean;
}

interface AgentDef {
  id: string;
  key: string;
  name: string;
  description: string;
  Icon: React.FC<{ className?: string }>;
  category: string;
}

interface ApiAgent {
  id: string;
  display_name: string;
  description: string;
  state: string;
  resource_name?: string;
  isFallback?: boolean;
}

/* ─── Static agent list (always shown in sidebar) ────────────────────────── */

const AGENTS: AgentDef[] = [
  { id: "trend", key: "trend_agent", name: "Trend Agent",
    description: "Spend trend analysis over time periods and categories",
    Icon: TrendingUp, category: "Analytics" },
  { id: "financial_leakage", key: "financial_leakage_agent", name: "Financial Leakage Agent",
    description: "Identifies unapproved spend, leakage risks and anomalies",
    Icon: AlertCircle, category: "Risk" },
  { id: "supplier_classification", key: "supplier_classification_agent", name: "Supplier Classification Agent",
    description: "Categorises suppliers by type, risk tier and spend band",
    Icon: Users, category: "Supplier" },
  { id: "buyer", key: "buyer_agent", name: "Buyer Agent",
    description: "Procurement and purchasing behaviour analysis",
    Icon: Search, category: "Procurement" },
  { id: "auditor", key: "auditor_agent", name: "Auditor Agent",
    description: "Audit, compliance and control gap analysis",
    Icon: Shield, category: "Compliance" },
  { id: "visualization", key: "visualization_agent", name: "Visualization Agent",
    description: "Generates charts and data visualisations from results",
    Icon: BarChart2, category: "Analytics" },
  { id: "contract_intelligence", key: "contract_intelligence_agent", name: "Contract Intelligence",
    description: "Contract compliance and invoice deviation analysis",
    Icon: FileText, category: "Compliance" },
  { id: "sql_generation", key: "sql_generation_agent", name: "SQL Generation Agent",
    description: "Generates optimised BigQuery SQL for financial datasets",
    Icon: Database, category: "Data" },
  { id: "spend_iq", key: "spend_iq_agent", name: "Spend IQ (Orchestrator)",
    description: "Master orchestrator — routes to the right specialist agent",
    Icon: Layers, category: "Orchestrator" },
];

/* ─── Helpers ─────────────────────────────────────────────────────────────── */

type BadgeVariant = "sandbox" | "manual" | "pending" | "live" | "fallback";

const BADGE_STYLES: Record<BadgeVariant, { wrap: string; dot: string }> = {
  sandbox:  { wrap: "bg-blue-50 text-blue-700 border-blue-200",    dot: "bg-blue-500" },
  manual:   { wrap: "bg-amber-50 text-amber-700 border-amber-200", dot: "bg-amber-400" },
  pending:  { wrap: "bg-gray-100 text-gray-500 border-gray-200",   dot: "bg-gray-400" },
  live:     { wrap: "bg-emerald-50 text-emerald-700 border-emerald-200", dot: "bg-emerald-500" },
  fallback: { wrap: "bg-yellow-50 text-yellow-800 border-yellow-300", dot: "bg-yellow-400" },
};

function StatusBadge({ label, variant }: { label: string; variant: BadgeVariant }) {
  const s = BADGE_STYLES[variant];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium border ${s.wrap}`}>
      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${s.dot}`} />
      {label}
    </span>
  );
}

function TypingDots() {
  return (
    <span className="inline-flex items-center gap-1 py-0.5">
      {[0, 1, 2].map((i) => (
        <span key={i} className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"
          style={{ animationDelay: `${i * 0.15}s`, animationDuration: "0.8s" }} />
      ))}
    </span>
  );
}

function MessageRow({ message, onCopy }: { message: Message; onCopy: (t: string) => void }) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);

  return (
    <div className={`flex gap-3 group ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
        ${isUser ? "bg-slate-600" : "bg-blue-700"}`}>
        {isUser ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4 text-white" />}
      </div>

      <div className={`flex flex-col ${isUser ? "items-end" : "items-start"} max-w-2xl`}>
        <div className={`px-4 py-3 rounded-lg text-sm leading-relaxed break-words
          ${isUser
            ? "bg-slate-700 text-white rounded-tr-none"
            : "bg-white border border-gray-200 text-gray-800 rounded-tl-none shadow-sm"}`}>
          {message.isTyping ? <TypingDots /> : (
            <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-code:bg-blue-50 prose-code:text-blue-700 prose-code:px-1 prose-code:rounded">
              <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        <div className={`flex items-center gap-2 mt-1 px-1 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
          <span className="text-[11px] text-gray-400 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>
          {message.status === "streaming" && (
            <span className="text-[11px] text-blue-600 font-medium">Processing…</span>
          )}
          {!message.isTyping && (
            <button
              onClick={() => { onCopy(message.content); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
              className="opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-gray-600"
              title="Copy">
              {copied ? <CheckCircle className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Main Component ──────────────────────────────────────────────────────── */

export default function SpendIntelligenceConsole() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState<AgentDef | null>(null);
  const [apiAgents, setApiAgents] = useState<ApiAgent[]>([]);
  const [isFallbackMode, setIsFallbackMode] = useState(false);
  const [agentId, setAgentId] = useState("");
  const [manualId, setManualId] = useState("");

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const sseRef = useRef<EventSource | null>(null);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  useEffect(() => {
    fetch("/api/agents")
      .then((r) => r.json())
      .then((d) => {
        setApiAgents(d.agents || []);
        setIsFallbackMode(!!d.isFallback);
      })
      .catch(() => setIsFallbackMode(true));
  }, []);

  function resolveAgentId(agent: AgentDef): string {
    const match = apiAgents.find((a) =>
      a.display_name?.toLowerCase().includes(agent.name.toLowerCase().split(" ")[0]) ||
      a.display_name?.toLowerCase().replace(/\s/g, "_").includes(agent.key.replace("_agent", ""))
    );
    if (!match || match.isFallback) return "";
    const parts = (match.resource_name || "").split("/");
    return parts[parts.length - 1] || match.id || "";
  }

  function handleSelectAgent(agent: AgentDef) {
    setSelectedAgent(agent);
    setMessages([]);
    setSessionId(undefined);
    setManualId("");
    setAgentId(resolveAgentId(agent));
    if (sseRef.current) { sseRef.current.close(); }
    setIsLoading(false);
  }

  const handleSend = useCallback(async () => {
    if (!input.trim() || isLoading || !selectedAgent) return;

    const effectiveId = agentId || manualId;

    const userMsg: Message = {
      id: Date.now().toString(),
      content: input.trim(),
      role: "user",
      timestamp: new Date(),
      status: "sent",
    };
    const typingMsg: Message = {
      id: (Date.now() + 1).toString(),
      content: "",
      role: "assistant",
      timestamp: new Date(),
      isTyping: true,
      status: "streaming",
    };

    if (!effectiveId) {
      setMessages((p) => [...p, userMsg, {
        id: (Date.now() + 1).toString(),
        content: `**${selectedAgent.name}** is not yet deployed to GCP.\n\nDeploy it from the company laptop, then refresh this page to test it here.`,
        role: "assistant",
        timestamp: new Date(),
        status: "error",
      }]);
      setInput("");
      return;
    }

    setMessages((p) => [...p, userMsg, typingMsg]);
    setInput("");
    setIsLoading(true);

    try {
      if (sseRef.current) sseRef.current.close();

      const params = new URLSearchParams({
        message: userMsg.content,
        agentId: effectiveId,
        ...(sessionId ? { sessionId } : {}),
      });

      const sse = new EventSource(`/api/agent-engine-stream?${params}`);
      sseRef.current = sse;
      let acc = "";
      const aid = typingMsg.id;

      sse.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.type === "session") { setSessionId(data.sessionId); return; }
          if (data.type === "content" && data.text) {
            acc += data.text;
            setMessages((p) => p.map((m) => m.id === aid ? { ...m, content: acc, isTyping: false, status: "streaming" } : m));
          }
          if (data.type === "done") {
            setMessages((p) => p.map((m) => m.id === aid ? { ...m, status: "sent", isTyping: false } : m));
            sse.close(); setIsLoading(false);
          }
          if (data.type === "error") {
            setMessages((p) => p.map((m) => m.id === aid ? { ...m, content: `Error: ${data.message}`, status: "error", isTyping: false } : m));
            sse.close(); setIsLoading(false);
          }
        } catch { /* ignore */ }
      };
      sse.onerror = () => {
        setMessages((p) => p.map((m) => m.id === aid ? { ...m, content: acc || "Connection error. Please retry.", status: "error", isTyping: false } : m));
        sse.close(); setIsLoading(false);
      };
    } catch {
      setMessages((p) => p.filter((m) => m.id !== typingMsg.id).concat({
        id: Date.now().toString(), content: "Failed to send. Please check your connection.",
        role: "assistant", timestamp: new Date(), status: "error",
      }));
      setIsLoading(false);
    }
  }, [input, isLoading, selectedAgent, agentId, manualId, sessionId]);

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  }

  function handleClearSession() {
    setMessages([]); setSessionId(undefined);
    if (sseRef.current) sseRef.current.close();
    setIsLoading(false);
  }

  const grouped = AGENTS.reduce<Record<string, AgentDef[]>>((acc, a) => {
    if (!acc[a.category]) acc[a.category] = [];
    acc[a.category].push(a);
    return acc;
  }, {});

  function isDeployed(agent: AgentDef): boolean {
    return apiAgents.some((a) => !a.isFallback && (
      a.display_name?.toLowerCase().includes(agent.name.toLowerCase().split(" ")[0]) ||
      a.display_name?.toLowerCase().replace(/\s/g, "_").includes(agent.key.replace("_agent", ""))
    ));
  }

  const effectiveId = agentId || manualId;

  return (
    <div style={{ fontFamily: '"Segoe UI", Arial, sans-serif' }}
      className="h-screen flex flex-col bg-gray-50 overflow-hidden text-gray-900">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header className="flex-shrink-0 bg-white border-b border-gray-200 h-14 px-4 flex items-center justify-between z-10 shadow-sm">
        <div className="flex items-center gap-3">
          <button onClick={() => setSidebarOpen((o) => !o)}
            className="p-1.5 rounded hover:bg-gray-100 text-gray-500 transition-colors" aria-label="Toggle sidebar">
            {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>

          <div className="flex items-center gap-2">
            {/* EY yellow accent logo */}
            <div className="w-7 h-7 rounded flex items-center justify-center" style={{ backgroundColor: "#ffe600" }}>
              <Activity className="w-4 h-4 text-gray-900" />
            </div>
            <div>
              <span className="text-sm font-semibold text-gray-900 tracking-tight">Spend Intelligence Console</span>
              <span className="ml-2 text-xs text-gray-400 hidden sm:inline">
                Supplier Cost Optimisation · GCP Sandbox
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isFallbackMode && <StatusBadge label="Sandbox Validation Mode" variant="fallback" />}
          {!isFallbackMode && <StatusBadge label="Sandbox Mode" variant="sandbox" />}
          <StatusBadge label="Manual Validation" variant="manual" />
          <StatusBadge label="Deployment Pending" variant="pending" />
        </div>
      </header>

      {/* ── Body ───────────────────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">

        {/* ── Sidebar ──────────────────────────────────────────────────────── */}
        {sidebarOpen && (
          <aside className="w-64 flex-shrink-0 bg-white border-r border-gray-200 flex flex-col overflow-y-auto">
            <div className="px-4 py-3 border-b border-gray-100">
              <p className="text-[11px] font-bold text-gray-400 uppercase tracking-widest">Agents</p>
              {isFallbackMode && (
                <p className="text-[11px] text-yellow-700 mt-1 leading-snug">
                  Sandbox Validation Mode — GCP not connected
                </p>
              )}
            </div>

            <nav className="flex-1 py-1">
              {Object.entries(grouped).map(([category, agents]) => (
                <div key={category}>
                  <p className="px-4 pt-3 pb-1 text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                    {category}
                  </p>
                  {agents.map((agent) => {
                    const deployed = isDeployed(agent);
                    const active = selectedAgent?.id === agent.id;
                    const { Icon } = agent;
                    return (
                      <button key={agent.id} onClick={() => handleSelectAgent(agent)}
                        className={`w-full flex items-start gap-2.5 px-4 py-2.5 text-left transition-colors border-r-2
                          ${active ? "bg-blue-50 border-blue-600" : "hover:bg-gray-50 border-transparent"}`}>
                        <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${active ? "text-blue-600" : "text-gray-400"}`} />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-1.5">
                            <span className={`text-sm font-medium truncate ${active ? "text-blue-700" : "text-gray-700"}`}>
                              {agent.name}
                            </span>
                            {/* deployment status dot */}
                            <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                              deployed ? "bg-emerald-500" : isFallbackMode ? "bg-yellow-400" : "bg-gray-300"
                            }`} />
                          </div>
                          <p className="text-[11px] text-gray-400 mt-0.5 leading-snug line-clamp-2">
                            {agent.description}
                          </p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              ))}
            </nav>

            {/* Legend */}
            <div className="px-4 py-3 border-t border-gray-100 flex items-center gap-3 text-[11px] text-gray-400">
              <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Deployed</span>
              <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-yellow-400" /> Sandbox</span>
              <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-gray-300" /> Pending</span>
            </div>
          </aside>
        )}

        {/* ── Workspace ────────────────────────────────────────────────────── */}
        <main className="flex-1 flex flex-col overflow-hidden">

          {/* Agent context bar */}
          <div className="flex-shrink-0 bg-white border-b border-gray-200 px-5 py-2 flex items-center justify-between min-h-[44px]">
            {selectedAgent ? (
              <>
                <div className="flex items-center gap-2.5">
                  <selectedAgent.Icon className="w-4 h-4 text-blue-600 flex-shrink-0" />
                  <span className="text-sm font-semibold text-gray-800">{selectedAgent.name}</span>
                  <span className="text-gray-300">|</span>
                  <span className="text-xs text-gray-500 truncate max-w-xs">{selectedAgent.description}</span>
                </div>
                <div className="flex items-center gap-2">
                  {sessionId && (
                    <span className="text-[11px] text-gray-400 font-mono hidden sm:inline">
                      Session: …{sessionId.slice(-6)}
                    </span>
                  )}
                  {effectiveId
                    ? <StatusBadge label="Live" variant="live" />
                    : isFallbackMode
                      ? <StatusBadge label="Sandbox Validation Mode" variant="fallback" />
                      : <StatusBadge label="Not deployed" variant="pending" />
                  }
                  <button onClick={handleClearSession}
                    className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-700 px-2 py-1 rounded hover:bg-gray-100 transition-colors">
                    <RefreshCw className="w-3 h-3" />
                    <span className="hidden sm:inline">New session</span>
                  </button>
                </div>
              </>
            ) : (
              <span className="text-xs text-gray-400">No agent selected</span>
            )}
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5 bg-gray-50">
            {messages.length === 0 && (
              <div className="h-full flex items-center justify-center">
                <div className="text-center max-w-md px-4">
                  {selectedAgent ? (
                    <>
                      <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center mx-auto mb-4">
                        <selectedAgent.Icon className="w-6 h-6 text-blue-600" />
                      </div>
                      <h3 className="text-base font-semibold text-gray-800 mb-1">{selectedAgent.name}</h3>
                      <p className="text-sm text-gray-500 mb-4">{selectedAgent.description}</p>
                      {effectiveId ? (
                        <p className="text-xs text-gray-400">Type a query below to start a sandbox validation.</p>
                      ) : isFallbackMode ? (
                        <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-3 text-left">
                          <p className="text-xs font-semibold text-yellow-800 mb-1">Sandbox Validation Mode</p>
                          <p className="text-xs text-yellow-700">
                            This agent is not yet deployed to GCP. You can still test queries by entering the Agent ID below,
                            or deploy from your company laptop first.
                          </p>
                        </div>
                      ) : (
                        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-left">
                          <p className="text-xs font-semibold text-amber-700 mb-1">Agent not yet deployed</p>
                          <p className="text-xs text-amber-600">Deploy from the company laptop, then refresh to test here.</p>
                        </div>
                      )}
                    </>
                  ) : (
                    <>
                      <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center mx-auto mb-4">
                        <ChevronRight className="w-6 h-6 text-gray-400" />
                      </div>
                      <h3 className="text-base font-semibold text-gray-700 mb-2">
                        Select an agent from the left panel to start a sandbox validation.
                      </h3>
                      <p className="text-sm text-gray-400">
                        Choose from Trend, Financial Leakage, Supplier Classification, and more.
                      </p>
                    </>
                  )}
                </div>
              </div>
            )}
            {messages.map((msg) => (
              <MessageRow key={msg.id} message={msg} onCopy={(t) => navigator.clipboard.writeText(t).catch(() => {})} />
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <div className="flex-shrink-0 bg-white border-t border-gray-200 px-5 py-3">
            {selectedAgent && !effectiveId && (
              <div className="mb-2 flex items-center gap-2">
                <span className="text-xs text-gray-500 flex-shrink-0">Agent ID:</span>
                <input
                  type="text"
                  value={manualId}
                  onChange={(e) => setManualId(e.target.value)}
                  placeholder="Enter numeric agent ID from Vertex AI (e.g. 3931281834880532480)"
                  className="flex-1 text-xs border border-gray-200 rounded px-2.5 py-1.5 text-gray-700 focus:outline-none focus:border-blue-400 transition-colors"
                />
              </div>
            )}

            <div className="flex items-end gap-3">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={!selectedAgent || isLoading}
                placeholder={
                  selectedAgent
                    ? `Ask ${selectedAgent.name} a question… (Enter to send, Shift+Enter for new line)`
                    : "Select an agent to start a query…"
                }
                rows={2}
                className={`flex-1 resize-none text-sm border rounded-lg px-3 py-2.5 focus:outline-none transition-colors
                  ${!selectedAgent || isLoading
                    ? "bg-gray-50 text-gray-400 border-gray-200 cursor-not-allowed"
                    : "bg-white text-gray-800 border-gray-300 focus:border-blue-500"}`}
                style={{ minHeight: "60px", maxHeight: "160px", lineHeight: "1.5" }}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || !selectedAgent || isLoading}
                className={`flex-shrink-0 flex items-center gap-1.5 px-4 py-2.5 rounded-lg text-sm font-medium transition-all
                  ${!input.trim() || !selectedAgent || isLoading
                    ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                    : "bg-blue-700 text-white hover:bg-blue-800 shadow-sm"}`}>
                {isLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                <span>{isLoading ? "Processing" : "Send"}</span>
              </button>
            </div>

            <div className="flex items-center justify-between mt-2">
              <span className="text-[11px] text-gray-400">
                EY GDS · SCO Multi-Agent Sandbox · Project: gp-ct-sbox-con-sbp0i2-eyenterp
              </span>
              <span className="text-[11px] text-gray-400">
                {messages.filter((m) => m.role === "user").length} queries this session
              </span>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
