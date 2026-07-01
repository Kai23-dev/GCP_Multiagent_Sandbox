"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  Send, Copy, CheckCircle, Clock, ChevronRight,
  AlertCircle, RefreshCw, Bot, User, Menu,
  BarChart2, TrendingUp, Shield, Search, Users,
  FileText, Activity, Database, Layers, Zap,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";
import "highlight.js/styles/github.css";

/* ── types ─────────────────────────────────────────────────────────────── */

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
  Icon: React.FC<{ className?: string; size?: number }>;
  category: string;
}

interface ApiAgent {
  id: string;
  display_name: string;
  state: string;
  resource_name?: string;
  isFallback?: boolean;
}

/* ── static agents ──────────────────────────────────────────────────────── */

const AGENTS: AgentDef[] = [
  { id: "trend",                key: "trend_agent",                  name: "Trend Agent",               description: "Spend trend analysis over time",             Icon: TrendingUp,  category: "Analytics"    },
  { id: "visualization",        key: "visualization_agent",          name: "Visualization Agent",       description: "Charts & data visualisations",               Icon: BarChart2,   category: "Analytics"    },
  { id: "financial_leakage",    key: "financial_leakage_agent",      name: "Financial Leakage",         description: "Unapproved spend & anomaly detection",       Icon: AlertCircle, category: "Risk"         },
  { id: "supplier_class",       key: "supplier_classification_agent",name: "Supplier Classification",   description: "Supplier risk tier & spend band",            Icon: Users,       category: "Supplier"     },
  { id: "buyer",                key: "buyer_agent",                  name: "Buyer Agent",               description: "Procurement behaviour analysis",             Icon: Search,      category: "Procurement"  },
  { id: "auditor",              key: "auditor_agent",                name: "Auditor Agent",             description: "Audit, compliance & control gaps",           Icon: Shield,      category: "Compliance"   },
  { id: "contract_intel",       key: "contract_intelligence_agent",  name: "Contract Intelligence",     description: "Invoice vs contract deviation",              Icon: FileText,    category: "Compliance"   },
  { id: "sql_gen",              key: "sql_generation_agent",         name: "SQL Generation",            description: "Generates BigQuery SQL",                     Icon: Database,    category: "Data"         },
  { id: "spend_iq",             key: "spend_iq_agent",              name: "Spend IQ",                  description: "Master orchestrator agent",                  Icon: Layers,      category: "Orchestrator" },
];

const CATEGORY_ORDER = ["Analytics","Risk","Supplier","Procurement","Compliance","Data","Orchestrator"];

/* ── typing dots ────────────────────────────────────────────────────────── */
function TypingDots() {
  return (
    <span className="flex gap-1 items-center h-5">
      {[0,1,2].map(i => (
        <span key={i} className="w-2 h-2 rounded-full animate-bounce"
          style={{ backgroundColor:"#9CA3AF", animationDelay:`${i*0.15}s`, animationDuration:"0.9s" }} />
      ))}
    </span>
  );
}

/* ── message bubble ─────────────────────────────────────────────────────── */
function Bubble({ msg, onCopy }: { msg: Message; onCopy: (t:string)=>void }) {
  const isUser = msg.role === "user";
  const [copied, setCopied] = useState(false);

  return (
    <div className={`flex gap-3 group ${isUser ? "flex-row-reverse" : "flex-row"} items-start`}>
      {/* avatar */}
      <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-white text-xs font-bold mt-0.5
        ${isUser ? "bg-gray-500" : ""}`}
        style={isUser ? {} : { background: "linear-gradient(135deg,#1F2937 0%,#374151 100%)", border:"2px solid #FFE600" }}>
        {isUser ? <User size={14} /> : <Bot size={14} />}
      </div>

      {/* bubble */}
      <div className={`flex flex-col ${isUser ? "items-end" : "items-start"} max-w-[70%]`}>
        <div className={`px-4 py-3 text-sm leading-relaxed rounded-2xl
          ${isUser
            ? "rounded-tr-sm text-white"
            : "rounded-tl-sm bg-white border border-gray-100 text-gray-800 shadow-sm"}`}
          style={isUser ? { background:"linear-gradient(135deg,#1F2937,#374151)" } : {}}>
          {msg.isTyping ? <TypingDots /> : (
            <div className="prose prose-sm max-w-none prose-code:bg-yellow-50 prose-code:text-yellow-800 prose-code:px-1 prose-code:rounded prose-headings:text-gray-900">
              <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                {msg.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        <div className={`flex items-center gap-2 mt-1 px-1 ${isUser ? "flex-row-reverse" : ""}`}>
          <span className="text-[10px] text-gray-400 flex items-center gap-1">
            <Clock size={10} />
            {msg.timestamp.toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"})}
          </span>
          {msg.status === "streaming" && <span className="text-[10px] font-medium" style={{color:"#FFE600"}}>Processing…</span>}
          {!msg.isTyping && (
            <button onClick={() => { onCopy(msg.content); setCopied(true); setTimeout(()=>setCopied(false),2000); }}
              className="opacity-0 group-hover:opacity-100 transition-opacity text-gray-300 hover:text-gray-500" title="Copy">
              {copied ? <CheckCircle size={12} className="text-green-500" /> : <Copy size={12} />}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── main ───────────────────────────────────────────────────────────────── */
export default function SpendIntelligenceConsole() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [selected, setSelected] = useState<AgentDef | null>(null);
  const [apiAgents, setApiAgents] = useState<ApiAgent[]>([]);
  const [isFallback, setIsFallback] = useState(false);
  const [agentId, setAgentId] = useState("");
  const [manualId, setManualId] = useState("");
  const [hoveredAgent, setHoveredAgent] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const sseRef = useRef<EventSource | null>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior:"smooth" }); }, [messages]);

  useEffect(() => {
    fetch("/api/agents").then(r=>r.json()).then(d=>{
      setApiAgents(d.agents||[]);
      setIsFallback(!!d.isFallback);
    }).catch(()=>setIsFallback(true));
  }, []);

  function resolveId(agent: AgentDef): string {
    const kw = agent.name.toLowerCase().split(" ")[0];
    const match = apiAgents.find(a=>!a.isFallback && a.display_name?.toLowerCase().includes(kw));
    if (!match) return "";
    const parts = (match.resource_name||"").split("/");
    return parts[parts.length-1] || match.id || "";
  }

  function selectAgent(agent: AgentDef) {
    setSelected(agent); setMessages([]); setSessionId(undefined);
    setManualId(""); setAgentId(resolveId(agent));
    sseRef.current?.close(); setIsLoading(false);
  }

  const send = useCallback(async () => {
    if (!input.trim() || isLoading || !selected) return;
    const eid = agentId || manualId;

    const uMsg: Message = { id: Date.now().toString(), content: input.trim(), role:"user", timestamp:new Date(), status:"sent" };
    const tMsg: Message = { id:(Date.now()+1).toString(), content:"", role:"assistant", timestamp:new Date(), isTyping:true, status:"streaming" };

    if (!eid) {
      setMessages(p=>[...p, uMsg, {
        id:(Date.now()+1).toString(),
        content:`**${selected.name}** is not deployed yet.\n\nPlease deploy it from the company laptop first, then enter the agent ID here to test.`,
        role:"assistant", timestamp:new Date(), status:"error"
      }]);
      setInput(""); return;
    }

    setMessages(p=>[...p, uMsg, tMsg]);
    setInput(""); setIsLoading(true);

    try {
      sseRef.current?.close();
      const params = new URLSearchParams({ message:uMsg.content, agentId:eid, ...(sessionId?{sessionId}:{}) });
      const sse = new EventSource(`/api/agent-engine-stream?${params}`);
      sseRef.current = sse;
      let acc = ""; const aid = tMsg.id;

      sse.onmessage = e => {
        try {
          const d = JSON.parse(e.data);
          if (d.type==="session") { setSessionId(d.sessionId); return; }
          if (d.type==="content"&&d.text) {
            acc+=d.text;
            setMessages(p=>p.map(m=>m.id===aid?{...m,content:acc,isTyping:false,status:"streaming"}:m));
          }
          if (d.type==="done") { setMessages(p=>p.map(m=>m.id===aid?{...m,status:"sent",isTyping:false}:m)); sse.close(); setIsLoading(false); }
          if (d.type==="error") { setMessages(p=>p.map(m=>m.id===aid?{...m,content:`Error: ${d.message}`,status:"error",isTyping:false}:m)); sse.close(); setIsLoading(false); }
        } catch { /* ignore */ }
      };
      sse.onerror = () => {
        setMessages(p=>p.map(m=>m.id===aid?{...m,content:acc||"Connection error. Please retry.",status:"error",isTyping:false}:m));
        sse.close(); setIsLoading(false);
      };
    } catch {
      setMessages(p=>p.filter(m=>m.id!==tMsg.id).concat({ id:Date.now().toString(), content:"Failed to send. Check your connection.", role:"assistant", timestamp:new Date(), status:"error" }));
      setIsLoading(false);
    }
  }, [input, isLoading, selected, agentId, manualId, sessionId]);

  const grouped = CATEGORY_ORDER.map(cat => ({ cat, agents: AGENTS.filter(a=>a.category===cat) })).filter(g=>g.agents.length>0);
  const eid = agentId || manualId;

  return (
    <div style={{ fontFamily:'"Segoe UI",system-ui,Arial,sans-serif', height:"100vh", display:"flex", flexDirection:"column", background:"#F0F2F5", overflow:"hidden" }}>

      {/* ── HEADER ─────────────────────────────────────────────────────── */}
      <header style={{ background:"#111827", borderBottom:"3px solid #FFE600", height:52, display:"flex", alignItems:"center", justifyContent:"space-between", padding:"0 20px", flexShrink:0 }}>
        <div style={{ display:"flex", alignItems:"center", gap:12 }}>
          <button onClick={()=>setSidebarOpen(o=>!o)}
            style={{ background:"none", border:"none", cursor:"pointer", color:"#9CA3AF", padding:4, borderRadius:6, display:"flex" }}
            onMouseEnter={e=>(e.currentTarget.style.color="#FFE600")}
            onMouseLeave={e=>(e.currentTarget.style.color="#9CA3AF")}>
            <Menu size={18} />
          </button>

          <div style={{ display:"flex", alignItems:"center", gap:10 }}>
            <div style={{ width:28, height:28, background:"#FFE600", borderRadius:6, display:"flex", alignItems:"center", justifyContent:"center" }}>
              <Activity size={16} color="#111827" />
            </div>
            <div>
              <div style={{ color:"#F9FAFB", fontSize:14, fontWeight:700, letterSpacing:"-0.01em", lineHeight:1 }}>
                Spend Intelligence Console
              </div>
              <div style={{ color:"#6B7280", fontSize:11, marginTop:2 }}>
                EY GDS · SCO Multi-Agent Sandbox
              </div>
            </div>
          </div>
        </div>

        <div style={{ display:"flex", gap:8, alignItems:"center" }}>
          {[
            { label: isFallback ? "Sandbox Validation Mode" : "Sandbox Mode", color:"#FFE600", bg:"rgba(255,230,0,0.12)", dot:"#FFE600" },
            { label:"Manual Validation", color:"#FCD34D", bg:"rgba(252,211,77,0.1)", dot:"#FCD34D" },
            { label:"Deployment Pending", color:"#6B7280", bg:"rgba(107,114,128,0.1)", dot:"#6B7280" },
          ].map(b=>(
            <span key={b.label} style={{ display:"inline-flex", alignItems:"center", gap:6, padding:"4px 10px", borderRadius:999, background:b.bg, color:b.color, fontSize:11, fontWeight:600, border:`1px solid ${b.color}30` }}>
              <span style={{ width:6, height:6, borderRadius:"50%", background:b.dot, flexShrink:0 }} />
              {b.label}
            </span>
          ))}
        </div>
      </header>

      {/* ── BODY ────────────────────────────────────────────────────────── */}
      <div style={{ display:"flex", flex:1, overflow:"hidden" }}>

        {/* ── SIDEBAR ─────────────────────────────────────────────────── */}
        {sidebarOpen && (
          <aside style={{ width:220, background:"#1F2937", display:"flex", flexDirection:"column", flexShrink:0, overflow:"hidden", borderRight:"1px solid #374151" }}>
            <div style={{ padding:"14px 16px 10px", borderBottom:"1px solid #374151" }}>
              <div style={{ color:"#9CA3AF", fontSize:10, fontWeight:700, letterSpacing:"0.1em", textTransform:"uppercase" }}>Agents</div>
              {isFallback && <div style={{ color:"#FFE600", fontSize:10, marginTop:4, lineHeight:1.4 }}>Sandbox Mode · GCP offline</div>}
            </div>

            <nav style={{ flex:1, overflowY:"auto", padding:"8px 0" }}>
              {grouped.map(({ cat, agents }) => (
                <div key={cat}>
                  <div style={{ color:"#4B5563", fontSize:10, fontWeight:700, letterSpacing:"0.08em", textTransform:"uppercase", padding:"10px 16px 4px" }}>{cat}</div>
                  {agents.map(agent => {
                    const isActive = selected?.id === agent.id;
                    const isHovered = hoveredAgent === agent.id;
                    const { Icon } = agent;
                    return (
                      <button key={agent.id}
                        onClick={()=>selectAgent(agent)}
                        onMouseEnter={()=>setHoveredAgent(agent.id)}
                        onMouseLeave={()=>setHoveredAgent(null)}
                        style={{
                          width:"100%", display:"flex", alignItems:"flex-start", gap:10,
                          padding:"9px 16px", textAlign:"left", border:"none", cursor:"pointer",
                          borderLeft: isActive ? "3px solid #FFE600" : "3px solid transparent",
                          background: isActive ? "rgba(255,230,0,0.08)" : isHovered ? "rgba(255,255,255,0.04)" : "transparent",
                          transition:"all 0.12s",
                        }}>
                        <Icon size={15} color={isActive ? "#FFE600" : "#6B7280"} style={{ marginTop:1, flexShrink:0 }} />
                        <div style={{ minWidth:0 }}>
                          <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                            <span style={{ fontSize:13, fontWeight: isActive ? 600 : 400, color: isActive ? "#F9FAFB" : "#D1D5DB", whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis" }}>
                              {agent.name}
                            </span>
                            <span style={{ width:5, height:5, borderRadius:"50%", background:isFallback?"#FFE600":"#374151", flexShrink:0 }} />
                          </div>
                          <div style={{ fontSize:11, color:"#6B7280", marginTop:1, lineHeight:1.3, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                            {agent.description}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              ))}
            </nav>

            <div style={{ borderTop:"1px solid #374151", padding:"10px 16px", display:"flex", gap:12, fontSize:10, color:"#4B5563" }}>
              <span style={{ display:"flex", alignItems:"center", gap:4 }}><span style={{ width:5,height:5,borderRadius:"50%",background:"#10B981" }} />Live</span>
              <span style={{ display:"flex", alignItems:"center", gap:4 }}><span style={{ width:5,height:5,borderRadius:"50%",background:"#FFE600" }} />Sandbox</span>
              <span style={{ display:"flex", alignItems:"center", gap:4 }}><span style={{ width:5,height:5,borderRadius:"50%",background:"#374151" }} />Pending</span>
            </div>
          </aside>
        )}

        {/* ── WORKSPACE ───────────────────────────────────────────────── */}
        <main style={{ flex:1, display:"flex", flexDirection:"column", overflow:"hidden" }}>

          {/* context bar */}
          <div style={{ background:"#fff", borderBottom:"1px solid #E5E7EB", padding:"0 20px", height:44, display:"flex", alignItems:"center", justifyContent:"space-between", flexShrink:0 }}>
            {selected ? (
              <>
                <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                  <selected.Icon size={15} color="#1F2937" />
                  <span style={{ fontSize:13, fontWeight:600, color:"#111827" }}>{selected.name}</span>
                  <span style={{ color:"#D1D5DB" }}>·</span>
                  <span style={{ fontSize:12, color:"#6B7280" }}>{selected.description}</span>
                </div>
                <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                  {sessionId && <span style={{ fontSize:11, color:"#9CA3AF", fontFamily:"monospace" }}>…{sessionId.slice(-6)}</span>}
                  <span style={{
                    padding:"3px 10px", borderRadius:999, fontSize:11, fontWeight:600,
                    background: eid ? "#D1FAE5" : isFallback ? "rgba(255,230,0,0.1)" : "#F3F4F6",
                    color: eid ? "#065F46" : isFallback ? "#92400E" : "#6B7280",
                    border: `1px solid ${eid?"#A7F3D0":isFallback?"#FFE600":"#E5E7EB"}`,
                  }}>
                    {eid ? "● Live" : isFallback ? "◐ Sandbox Validation Mode" : "○ Not deployed"}
                  </span>
                  <button onClick={()=>{ setMessages([]); setSessionId(undefined); sseRef.current?.close(); setIsLoading(false); }}
                    style={{ display:"flex", alignItems:"center", gap:5, fontSize:12, color:"#9CA3AF", background:"none", border:"1px solid #E5E7EB", borderRadius:6, padding:"4px 10px", cursor:"pointer" }}
                    onMouseEnter={e=>{e.currentTarget.style.color="#1F2937";e.currentTarget.style.borderColor="#9CA3AF"}}
                    onMouseLeave={e=>{e.currentTarget.style.color="#9CA3AF";e.currentTarget.style.borderColor="#E5E7EB"}}>
                    <RefreshCw size={11} /> New session
                  </button>
                </div>
              </>
            ) : (
              <span style={{ fontSize:12, color:"#9CA3AF" }}>← Select an agent to get started</span>
            )}
          </div>

          {/* messages */}
          <div style={{ flex:1, overflowY:"auto", padding:"24px 28px", display:"flex", flexDirection:"column", gap:18 }}>
            {messages.length === 0 && (
              <div style={{ flex:1, display:"flex", alignItems:"center", justifyContent:"center" }}>
                <div style={{ textAlign:"center", maxWidth:380 }}>
                  {selected ? (
                    <>
                      <div style={{ width:52,height:52,borderRadius:14,background:"#1F2937",display:"flex",alignItems:"center",justifyContent:"center",margin:"0 auto 16px",border:"2px solid #FFE600" }}>
                        <selected.Icon size={24} color="#FFE600" />
                      </div>
                      <div style={{ fontSize:17, fontWeight:700, color:"#111827", marginBottom:6 }}>{selected.name}</div>
                      <div style={{ fontSize:13, color:"#6B7280", marginBottom:16, lineHeight:1.5 }}>{selected.description}</div>
                      {eid ? (
                        <div style={{ fontSize:12, color:"#6B7280" }}>Type a query below to start a sandbox validation.</div>
                      ) : (
                        <div style={{ background:"#FFFBEB", border:"1px solid #FDE68A", borderRadius:10, padding:"12px 16px", textAlign:"left" }}>
                          <div style={{ fontSize:12, fontWeight:700, color:"#92400E", marginBottom:4 }}>Sandbox Validation Mode</div>
                          <div style={{ fontSize:12, color:"#78350F", lineHeight:1.5 }}>
                            Enter the Agent ID below to test, or deploy this agent from the company laptop first.
                          </div>
                        </div>
                      )}
                    </>
                  ) : (
                    <>
                      <div style={{ width:52,height:52,borderRadius:14,background:"#F3F4F6",display:"flex",alignItems:"center",justifyContent:"center",margin:"0 auto 16px" }}>
                        <ChevronRight size={24} color="#9CA3AF" />
                      </div>
                      <div style={{ fontSize:16, fontWeight:600, color:"#374151", marginBottom:8 }}>
                        Select an agent from the left panel to start a sandbox validation.
                      </div>
                      <div style={{ fontSize:13, color:"#9CA3AF", lineHeight:1.5 }}>
                        Choose from Trend Analysis, Financial Leakage, Supplier Classification, and more.
                      </div>
                    </>
                  )}
                </div>
              </div>
            )}
            {messages.map(m=>(
              <Bubble key={m.id} msg={m} onCopy={t=>navigator.clipboard.writeText(t).catch(()=>{})} />
            ))}
            <div ref={bottomRef} />
          </div>

          {/* input area */}
          <div style={{ background:"#fff", borderTop:"1px solid #E5E7EB", padding:"14px 20px", flexShrink:0 }}>
            {selected && !eid && (
              <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:10 }}>
                <Zap size={13} color="#FFE600" />
                <span style={{ fontSize:12, color:"#6B7280", flexShrink:0 }}>Agent ID:</span>
                <input type="text" value={manualId} onChange={e=>setManualId(e.target.value)}
                  placeholder="Enter numeric agent ID from Vertex AI…"
                  style={{ flex:1, fontSize:12, border:"1px solid #E5E7EB", borderRadius:6, padding:"5px 10px", color:"#1F2937", outline:"none", fontFamily:"monospace" }}
                  onFocus={e=>e.currentTarget.style.borderColor="#FFE600"}
                  onBlur={e=>e.currentTarget.style.borderColor="#E5E7EB"}
                />
              </div>
            )}

            <div style={{ display:"flex", gap:10, alignItems:"flex-end" }}>
              <textarea ref={inputRef} value={input} onChange={e=>setInput(e.target.value)}
                onKeyDown={e=>{ if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send();} }}
                disabled={!selected||isLoading}
                placeholder={selected ? `Ask ${selected.name} a question… (Enter to send)` : "Select an agent to begin…"}
                rows={2}
                style={{
                  flex:1, resize:"none", fontSize:13, border:"1px solid #E5E7EB", borderRadius:10,
                  padding:"10px 14px", outline:"none", fontFamily:"inherit", lineHeight:1.5,
                  color:"#111827", background:(!selected||isLoading)?"#F9FAFB":"#fff",
                  minHeight:56, maxHeight:140, transition:"border-color 0.15s",
                }}
                onFocus={e=>{if(selected&&!isLoading)e.currentTarget.style.borderColor="#1F2937"}}
                onBlur={e=>e.currentTarget.style.borderColor="#E5E7EB"}
              />
              <button onClick={send} disabled={!input.trim()||!selected||isLoading}
                style={{
                  flexShrink:0, display:"flex", alignItems:"center", gap:6,
                  padding:"10px 18px", borderRadius:10, fontSize:13, fontWeight:600,
                  border:"none", cursor:(!input.trim()||!selected||isLoading)?"not-allowed":"pointer",
                  background:(!input.trim()||!selected||isLoading)?"#F3F4F6":"#111827",
                  color:(!input.trim()||!selected||isLoading)?"#9CA3AF":"#FFE600",
                  transition:"all 0.15s",
                  height:56,
                }}
                onMouseEnter={e=>{ if(input.trim()&&selected&&!isLoading) e.currentTarget.style.background="#FFE600"; e.currentTarget.style.color="#111827"; }}
                onMouseLeave={e=>{ if(input.trim()&&selected&&!isLoading) e.currentTarget.style.background="#111827"; e.currentTarget.style.color="#FFE600"; }}>
                {isLoading ? <RefreshCw size={15} style={{ animation:"spin 1s linear infinite" }} /> : <Send size={15} />}
                {isLoading ? "Processing" : "Send"}
              </button>
            </div>

            <div style={{ display:"flex", justifyContent:"space-between", marginTop:8, fontSize:11, color:"#9CA3AF" }}>
              <span>EY GDS · gp-ct-sbox-con-sbp0i2-eyenterp · us-central1</span>
              <span>{messages.filter(m=>m.role==="user").length} queries this session</span>
            </div>
          </div>
        </main>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #374151; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #4B5563; }
      `}</style>
    </div>
  );
}
