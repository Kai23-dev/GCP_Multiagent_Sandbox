"use client";

import { ArrowRight, Clock, Zap } from "lucide-react";

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

interface ProcessNode {
  id: string;
  label: string;
  agentName: string;
  durationMs: number;
  startTime: number;
  endTime: number;
  type: "agent" | "tool" | "llm" | "transfer";
  isError: boolean;
  children: ProcessNode[];
}

const AGENT_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  spendiq: { bg: "bg-blue-50", border: "border-blue-400", text: "text-blue-700" },
  auditor: { bg: "bg-emerald-50", border: "border-emerald-400", text: "text-emerald-700" },
  buyer: { bg: "bg-purple-50", border: "border-purple-400", text: "text-purple-700" },
  trend: { bg: "bg-amber-50", border: "border-amber-400", text: "text-amber-700" },
  supplier: { bg: "bg-rose-50", border: "border-rose-400", text: "text-rose-700" },
  contract: { bg: "bg-cyan-50", border: "border-cyan-400", text: "text-cyan-700" },
  financial: { bg: "bg-orange-50", border: "border-orange-400", text: "text-orange-700" },
  visualization: { bg: "bg-indigo-50", border: "border-indigo-400", text: "text-indigo-700" },
  sql: { bg: "bg-teal-50", border: "border-teal-400", text: "text-teal-700" },
  validation: { bg: "bg-lime-50", border: "border-lime-400", text: "text-lime-700" },
};

function getNodeColors(name: string): { bg: string; border: string; text: string } {
  const lower = (name || "").toLowerCase();
  for (const [key, colors] of Object.entries(AGENT_COLORS)) {
    if (lower.includes(key)) return colors;
  }
  return { bg: "bg-gray-50", border: "border-gray-300", text: "text-gray-700" };
}

function formatDuration(ms: number): string {
  if (ms >= 60000) return `${(ms / 60000).toFixed(1)}m`;
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.round(ms)}ms`;
}

function getSpanType(name: string): "agent" | "tool" | "llm" | "transfer" {
  if (name === "transfer_to_agent") return "transfer";
  if (name === "call_llm" || name.startsWith("generate_content")) return "llm";
  if (name.startsWith("execute_tool")) return "tool";
  if (name === "invocation" || name === "invoke_agent" || name.startsWith("invoke_agent") || /query_\w+/.test(name)) return "agent";
  return "tool";
}

function getSpanLabel(span: Span): string {
  const name = span.name || "";
  if (span.agentName && (name === "invocation" || name === "invoke_agent" || name === "transfer_to_agent")) {
    return span.agentName;
  }
  if (name.startsWith("invoke_agent ")) return name.replace(/^invoke_agent\s*/, "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  if (name.startsWith("execute_tool ")) return name.replace(/^execute_tool\s*/, "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  if (name === "execute_tool") return span.agentName ? `${span.agentName} Tool` : "Tool";
  const qm = name.match(/^query_(\w+?)(?:_agent)?$/);
  if (qm) return qm[1].replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  if (name === "call_llm") return span.agentName ? `${span.agentName} LLM` : "LLM Call";
  if (name.startsWith("generate_content")) return "LLM Generation";
  if (/^\d+$/.test(name)) return "Remote Agent Call";
  return name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function buildProcessTree(spans: Span[]): ProcessNode[] {
  const byId = new Map(spans.map((s) => [s.spanId, s]));
  const childMap = new Map<string, Span[]>();

  for (const span of spans) {
    const pid = span.parentSpanId || "__root__";
    if (!childMap.has(pid)) childMap.set(pid, []);
    childMap.get(pid)!.push(span);
  }

  function isSignificant(span: Span): boolean {
    const name = span.name || "";
    return (
      name === "invocation" ||
      name === "invoke_agent" ||
      name.startsWith("invoke_agent ") ||
      name === "transfer_to_agent" ||
      name === "call_llm" ||
      name.startsWith("execute_tool") ||
      /query_\w+/.test(name) ||
      /^\d+$/.test(name)
    );
  }

  function buildNode(span: Span): ProcessNode {
    const startMs = new Date(span.startTime).getTime();
    const endMs = new Date(span.endTime).getTime();
    const kids = (childMap.get(span.spanId) || [])
      .sort((a, b) => new Date(a.startTime).getTime() - new Date(b.startTime).getTime());

    const significantKids = kids.filter(isSignificant);
    // If no significant children, check deeper
    const childNodes: ProcessNode[] = [];
    for (const kid of significantKids) {
      childNodes.push(buildNode(kid));
    }
    // Also look for significant spans nested deeper
    for (const kid of kids) {
      if (!isSignificant(kid)) {
        const deepKids = (childMap.get(kid.spanId) || []).filter(isSignificant);
        for (const dk of deepKids) {
          childNodes.push(buildNode(dk));
        }
      }
    }

    return {
      id: span.spanId,
      label: getSpanLabel(span),
      agentName: span.agentName || "",
      durationMs: endMs - startMs,
      startTime: startMs,
      endTime: endMs,
      type: getSpanType(span.name),
      isError: span.status?.code === 2,
      children: childNodes.sort((a, b) => a.startTime - b.startTime),
    };
  }

  const rootSpans = spans.filter(
    (s) => !s.parentSpanId || !byId.has(s.parentSpanId)
  ).sort((a, b) => new Date(a.startTime).getTime() - new Date(b.startTime).getTime());

  return rootSpans.map(buildNode);
}

function ProcessNodeCard({ node, depth = 0 }: { node: ProcessNode; depth?: number }) {
  const colors = getNodeColors(node.agentName || node.label);
  const isAgent = node.type === "agent" || node.type === "transfer";

  const typeIcon = {
    agent: "🤖",
    transfer: "↪️",
    tool: "🔧",
    llm: "⚡",
  }[node.type];

  return (
    <div className="flex flex-col items-center">
      <div
        className={`rounded-lg border-2 px-4 py-3 min-w-[160px] max-w-[220px] shadow-sm transition-all hover:shadow-md ${
          node.isError ? "border-red-400 bg-red-50" : `${colors.border} ${colors.bg}`
        }`}
      >
        <div className="flex items-center gap-1.5 mb-1">
          <span className="text-sm">{typeIcon}</span>
          <span className={`text-xs font-bold truncate ${node.isError ? "text-red-700" : colors.text}`}>
            {node.label}
          </span>
        </div>
        <div className="flex items-center gap-2 text-[11px]">
          <span className={`flex items-center gap-0.5 font-semibold ${
            node.durationMs > 15000 ? "text-red-600" : node.durationMs > 5000 ? "text-amber-600" : "text-gray-600"
          }`}>
            <Clock className="w-3 h-3" />
            {formatDuration(node.durationMs)}
          </span>
          {isAgent && node.children.length > 0 && (
            <span className="text-gray-400">
              {node.children.length} step{node.children.length > 1 ? "s" : ""}
            </span>
          )}
        </div>
      </div>

      {node.children.length > 0 && (
        <>
          <div className="w-px h-4 bg-gray-300" />
          <div className="flex items-start gap-3 relative">
            {node.children.length > 1 && (
              <div
                className="absolute top-0 border-t-2 border-gray-200"
                style={{
                  left: "50%",
                  width: `${(node.children.length - 1) * 100}%`,
                  transform: "translateX(-50%)",
                }}
              />
            )}
            {node.children.map((child, i) => (
              <div key={child.id} className="flex flex-col items-center">
                <div className="w-px h-4 bg-gray-300" />
                <ProcessNodeCard node={child} depth={depth + 1} />
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default function ProcessMap({ spans }: { spans: Span[] }) {
  if (!spans || spans.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        No spans found to build process map
      </div>
    );
  }

  const allStartMs = spans.map((s) => new Date(s.startTime).getTime());
  const allEndMs = spans.map((s) => new Date(s.endTime).getTime());
  const totalMs = Math.max(...allEndMs) - Math.min(...allStartMs);

  const tree = buildProcessTree(spans);

  // Build a flat sequence of agents for the flow summary
  const agentSequence: { name: string; durationMs: number; color: string }[] = [];
  function extractAgentFlow(nodes: ProcessNode[]) {
    for (const n of nodes) {
      if (n.type === "agent" || n.type === "transfer") {
        agentSequence.push({
          name: n.label,
          durationMs: n.durationMs,
          color: getNodeColors(n.agentName || n.label).border.replace("border-", "bg-").replace("-400", "-500"),
        });
      }
      extractAgentFlow(n.children);
    }
  }
  extractAgentFlow(tree);

  return (
    <div className="border rounded-lg bg-white shadow-sm overflow-hidden">
      {/* Flow Summary */}
      <div className="border-b bg-gradient-to-r from-gray-50 to-white px-4 py-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">
            Execution Flow
          </span>
          <span className="text-sm font-bold text-gray-800">
            Total: {formatDuration(totalMs)}
          </span>
        </div>
        <div className="flex items-center gap-1 flex-wrap">
          {agentSequence.map((item, i) => (
            <span key={i} className="flex items-center gap-1">
              {i > 0 && <ArrowRight className="w-3 h-3 text-gray-400" />}
              <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium text-white ${item.color}`}>
                {item.name}
                <span className="opacity-80">{formatDuration(item.durationMs)}</span>
              </span>
            </span>
          ))}
        </div>
      </div>

      {/* Tree Visualization */}
      <div className="p-6 overflow-x-auto">
        <div className="flex justify-center gap-6">
          {tree.map((root) => (
            <ProcessNodeCard key={root.id} node={root} />
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="border-t bg-gray-50 px-4 py-2 flex items-center gap-6 text-xs text-gray-500">
        <span className="flex items-center gap-1">🤖 Agent</span>
        <span className="flex items-center gap-1">↪️ Transfer</span>
        <span className="flex items-center gap-1">🔧 Tool</span>
        <span className="flex items-center gap-1">⚡ LLM Call</span>
        <span className="ml-auto flex items-center gap-1">
          <Zap className="w-3 h-3" />
          {spans.length} total spans
        </span>
      </div>
    </div>
  );
}
