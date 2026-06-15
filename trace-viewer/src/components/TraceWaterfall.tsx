"use client";

import { useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  ChevronDown,
  ChevronRight,
  Clock,
  Zap,
} from "lucide-react";

interface Span {
  spanId: string;
  name: string;
  parentSpanId?: string;
  startTime: string;
  endTime: string;
  status?: { code: number; message?: string };
  attributes?: Record<string, { stringValue?: string; intValue?: string }>;
  agentName?: string;
}

interface Props {
  spans: Span[];
  onSpanClick?: (span: Span) => void;
  selectedSpanId?: string;
}

const AGENT_COLORS: Record<string, string> = {
  spendiq: "bg-blue-600",
  auditor: "bg-emerald-500",
  buyer: "bg-purple-500",
  trend: "bg-amber-500",
  supplier: "bg-rose-500",
  contract: "bg-cyan-500",
  financial: "bg-orange-500",
  visualization: "bg-indigo-500",
  sql: "bg-teal-500",
  validation: "bg-lime-600",
};

function getAgentColor(name: string): string {
  const lower = (name || "").toLowerCase();
  for (const [key, color] of Object.entries(AGENT_COLORS)) {
    if (lower.includes(key)) return color;
  }
  return "bg-gray-400";
}

const AGENT_DISPLAY_NAMES: Record<string, string> = {
  spend_iq_agent: "SpendIQ",
  spend_iq: "SpendIQ",
  auditor_agent: "Auditor",
  auditor: "Auditor",
  buyer_agent: "Buyer",
  buyer: "Buyer",
  trend_agent: "Trend Analyst",
  trend: "Trend Analyst",
  supplier_classification_agent: "Supplier Classification",
  supplier_classification: "Supplier Classification",
  contract_intelligence_agent: "Contract Intelligence",
  contract_intelligence: "Contract Intelligence",
  financial_leakage_agent: "Financial Leakage",
  financial_leakage: "Financial Leakage",
  visualization_agent: "Visualization",
  visualization: "Visualization",
  sql_generation_agent: "SQL Generation",
  sql_generation: "SQL Generation",
  sql_execution_agent: "SQL Execution",
  sql_execution: "SQL Execution",
  validation_agent: "Validation",
  validation: "Validation",
};

function resolveAgentDisplayName(raw: string): string {
  if (!raw) return "";
  const lower = raw.toLowerCase().replace(/[-\s]/g, "_");
  return (
    AGENT_DISPLAY_NAMES[lower] ||
    raw.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
  );
}

const SPAN_DISPLAY: Record<string, string> = {
  invocation: "Request",
  invoke_agent: "Agent Call",
  call_llm: "LLM Call",
  transfer_to_agent: "Route to Agent",
};

function getSpanLabel(span: Span): string {
  const name = span.name || "";
  if (span.agentName && (name === "invocation" || name === "invoke_agent" || name === "transfer_to_agent")) {
    return span.agentName;
  }
  if (name.startsWith("invoke_agent ")) {
    const agentRaw = name.replace(/^invoke_agent\s*/, "");
    return resolveAgentDisplayName(agentRaw) || span.agentName || "Agent Call";
  }
  if (name.startsWith("execute_tool ")) {
    const toolRaw = name.replace(/^execute_tool\s*/, "");
    return toolRaw.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }
  if (name === "execute_tool") {
    return span.agentName ? `${span.agentName} Tool` : "Tool Call";
  }
  const queryMatch = name.match(/^query_(\w+?)(?:_agent)?$/);
  if (queryMatch) return resolveAgentDisplayName(queryMatch[1]) || span.agentName || queryMatch[1];
  if (name === "call_llm") {
    return span.agentName ? `${span.agentName} LLM Call` : "LLM Call";
  }
  if (name.startsWith("generate_content")) return "LLM Generation";
  if (/^\d+$/.test(name)) return "Remote Agent Call";
  return SPAN_DISPLAY[name] || name;
}

function isAgentSpan(span: Span): boolean {
  return (
    span.name === "invocation" ||
    span.name === "invoke_agent" ||
    /query_\w+/.test(span.name) ||
    span.name === "transfer_to_agent" ||
    span.name === "call_llm"
  );
}

function formatDuration(ms: number): string {
  if (ms >= 60000) return `${(ms / 60000).toFixed(1)}m`;
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.round(ms)}ms`;
}

function AgentSummary({ spans }: { spans: Span[] }) {
  const agentSpans = spans.filter(
    (s) =>
      s.name === "transfer_to_agent" ||
      s.name === "invoke_agent" ||
      s.name === "invocation" ||
      /query_\w+/.test(s.name)
  );
  if (agentSpans.length === 0) return null;

  const allStartMs = spans.map((s) => new Date(s.startTime).getTime());
  const allEndMs = spans.map((s) => new Date(s.endTime).getTime());
  const totalMs = Math.max(...allEndMs) - Math.min(...allStartMs);

  const root = agentSpans.find((s) => s.name === "invocation");
  const childAgents = agentSpans
    .filter(
      (s) =>
        s.name === "transfer_to_agent" ||
        /query_\w+/.test(s.name)
    )
    .sort(
      (a, b) =>
        new Date(a.startTime).getTime() - new Date(b.startTime).getTime()
    );

  const chain: { name: string; durationMs: number; color: string }[] = [];
  if (root) {
    chain.push({
      name: root.agentName || "Orchestrator",
      durationMs: new Date(root.endTime).getTime() - new Date(root.startTime).getTime(),
      color: getAgentColor(root.agentName || root.name),
    });
  }
  for (const s of childAgents) {
    const label = getSpanLabel(s);
    const dur = new Date(s.endTime).getTime() - new Date(s.startTime).getTime();
    chain.push({
      name: label,
      durationMs: dur,
      color: getAgentColor(s.agentName || s.name),
    });
  }

  return (
    <div className="border-b bg-gradient-to-r from-gray-50 to-white px-4 py-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">
          Agent Flow
        </span>
        <span className="text-sm font-bold text-gray-800">
          Total: {formatDuration(totalMs)}
        </span>
      </div>
      <div className="flex items-center gap-1 flex-wrap">
        {chain.map((item, i) => (
          <span key={i} className="flex items-center gap-1">
            {i > 0 && <ArrowRight className="w-3 h-3 text-gray-400" />}
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium text-white ${item.color}`}
            >
              {item.name}
              <span className="opacity-80">{formatDuration(item.durationMs)}</span>
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}

interface TreeNode {
  span: Span;
  children: TreeNode[];
  depth: number;
}

function buildTree(spans: Span[]): TreeNode[] {
  const byId = new Map(spans.map((s) => [s.spanId, s]));
  const childMap = new Map<string, Span[]>();

  for (const span of spans) {
    const pid = span.parentSpanId || "__root__";
    if (!childMap.has(pid)) childMap.set(pid, []);
    childMap.get(pid)!.push(span);
  }

  function build(parentId: string, depth: number): TreeNode[] {
    const kids = childMap.get(parentId) || [];
    kids.sort(
      (a, b) =>
        new Date(a.startTime).getTime() - new Date(b.startTime).getTime()
    );
    return kids.map((span) => ({
      span,
      depth,
      children: build(span.spanId, depth + 1),
    }));
  }

  const rootSpans = spans.filter(
    (s) => !s.parentSpanId || !byId.has(s.parentSpanId)
  );
  return rootSpans.map((s) => ({
    span: s,
    depth: 0,
    children: build(s.spanId, 1),
  }));
}

function SpanRow({
  node,
  traceStart,
  traceDuration,
  onSpanClick,
  selectedSpanId,
  defaultExpanded,
}: {
  node: TreeNode;
  traceStart: number;
  traceDuration: number;
  onSpanClick?: (span: Span) => void;
  selectedSpanId?: string;
  defaultExpanded: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const { span, children, depth } = node;

  const startMs = new Date(span.startTime).getTime();
  const endMs = new Date(span.endTime).getTime();
  const duration = endMs - startMs;
  const leftPct = ((startMs - traceStart) / traceDuration) * 100;
  const widthPct = Math.max((duration / traceDuration) * 100, 0.5);
  const isError = span.status?.code === 2;
  const isSelected = span.spanId === selectedSpanId;
  const label = getSpanLabel(span);
  const color = getAgentColor(span.agentName || span.name);
  const hasChildren = children.length > 0;
  const isTopLevel = isAgentSpan(span);

  return (
    <>
      <div
        className={`grid grid-cols-[340px_1fr] cursor-pointer transition-colors ${
          isSelected
            ? "bg-blue-50 ring-1 ring-blue-300"
            : isTopLevel
            ? "hover:bg-blue-50"
            : "hover:bg-gray-50"
        } ${!isTopLevel ? "opacity-75" : ""}`}
        onClick={() => onSpanClick?.(span)}
      >
        <div className="px-4 py-1.5 flex items-center gap-1 min-w-0">
          <div
            style={{ marginLeft: `${depth * 20}px` }}
            className="flex items-center gap-1.5 min-w-0"
          >
            {hasChildren ? (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setExpanded(!expanded);
                }}
                className="p-0.5 hover:bg-gray-200 rounded"
              >
                {expanded ? (
                  <ChevronDown className="w-3.5 h-3.5 text-gray-500" />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5 text-gray-500" />
                )}
              </button>
            ) : (
              <span className="w-4.5" />
            )}
            <div
              className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
                isError ? "bg-red-500" : color
              }`}
            />
            <span
              className={`text-sm truncate ${
                isTopLevel ? "font-semibold text-gray-900" : "text-gray-600"
              }`}
              title={span.name}
            >
              {label}
            </span>
          </div>
        </div>

        <div className="px-4 py-1.5 relative">
          <div
            className={`absolute top-1/2 -translate-y-1/2 rounded-sm flex items-center px-1.5 text-[10px] text-white font-medium ${
              isError ? "bg-red-500" : color
            } ${isTopLevel ? "h-6" : "h-4 opacity-70"}`}
            style={{
              left: `${leftPct}%`,
              width: `${widthPct}%`,
              minWidth: "40px",
            }}
          >
            {formatDuration(duration)}
            {isError && <AlertCircle className="w-3 h-3 ml-1 inline" />}
          </div>
        </div>
      </div>

      {expanded &&
        children.map((child) => (
          <SpanRow
            key={child.span.spanId}
            node={child}
            traceStart={traceStart}
            traceDuration={traceDuration}
            onSpanClick={onSpanClick}
            selectedSpanId={selectedSpanId}
            defaultExpanded={isAgentSpan(child.span)}
          />
        ))}
    </>
  );
}

export default function TraceWaterfall({
  spans,
  onSpanClick,
  selectedSpanId,
}: Props) {
  if (!spans || spans.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        No spans found in this trace
      </div>
    );
  }

  const allStartMs = spans.map((s) => new Date(s.startTime).getTime());
  const allEndMs = spans.map((s) => new Date(s.endTime).getTime());
  const traceStart = Math.min(...allStartMs);
  const traceEnd = Math.max(...allEndMs);
  const traceDuration = traceEnd - traceStart || 1;

  const tree = buildTree(spans);

  const quarter = traceDuration / 4;

  return (
    <div className="border rounded-lg bg-white shadow-sm overflow-hidden">
      <AgentSummary spans={spans} />

      <div className="grid grid-cols-[340px_1fr] border-b bg-gray-50 text-xs font-medium text-gray-500 uppercase tracking-wider">
        <div className="px-4 py-2">Agent / Step</div>
        <div className="px-4 py-2 flex justify-between">
          <span>0s</span>
          <span>{formatDuration(quarter)}</span>
          <span>{formatDuration(quarter * 2)}</span>
          <span>{formatDuration(quarter * 3)}</span>
          <span>{formatDuration(traceDuration)}</span>
        </div>
      </div>

      <div className="divide-y divide-gray-100">
        {tree.map((node) => (
          <SpanRow
            key={node.span.spanId}
            node={node}
            traceStart={traceStart}
            traceDuration={traceDuration}
            onSpanClick={onSpanClick}
            selectedSpanId={selectedSpanId}
            defaultExpanded={true}
          />
        ))}
      </div>

      <div className="border-t bg-gray-50 px-4 py-2 flex items-center gap-4 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <Zap className="w-3 h-3" />
          {spans.length} steps
        </span>
        <span className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          Total: {formatDuration(traceDuration)}
        </span>
      </div>
    </div>
  );
}
