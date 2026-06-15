import { getAccessToken, getProjectId } from "./gcp-auth";

export interface TraceSpan {
  spanId: string;
  name: string;
  parentSpanId?: string;
  startTime: string;
  endTime: string;
  status?: { code: number; message?: string };
  attributes?: Record<string, { stringValue?: string; intValue?: string }>;
  agentName?: string;
}

export interface Trace {
  traceId: string;
  spans: TraceSpan[];
  projectId: string;
}

export interface TraceListItem {
  traceId: string;
  agentName: string;
  subAgents: string[];
  startTime: string;
  duration: number;
  netDuration: number;
  spanCount: number;
  hasError: boolean;
  agentTimings: Record<string, number>;
  invocationId?: string;
  childTraceIds?: string[];
  subAgentIntervals?: [number, number][];
}

export interface AgentStats {
  agentName: string;
  avgDuration: number;
  requestCount: number;
  errorCount: number;
  p90Duration: number;
  isAgent: boolean;
  children: AgentStats[];
}

const CLOUD_TRACE_V1 = "https://cloudtrace.googleapis.com/v1";

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

export function getAgentDisplayName(raw: string): string {
  if (!raw) return "Unknown";
  const lower = raw.toLowerCase().replace(/[-\s]/g, "_");
  return AGENT_DISPLAY_NAMES[lower] || raw.replace(/_/g, " ").replace(/\b\w/g, (ch: string) => ch.toUpperCase());
}

export async function listTraces(opts: {
  startDate?: string;
  endDate?: string;
  minutes?: number;
  pageSize?: number;
  filter?: string;
}): Promise<{ traces: TraceListItem[]; stats: AgentStats[] }> {
  const projectId = getProjectId();
  const token = await getAccessToken();

  const endTime = opts.endDate
    ? new Date(opts.endDate + "T23:59:59Z").toISOString()
    : new Date().toISOString();
  const startTime = opts.startDate
    ? new Date(opts.startDate + "T00:00:00Z").toISOString()
    : new Date(Date.now() - (opts.minutes || 60) * 60 * 1000).toISOString();

  const params: Record<string, string> = {
    startTime,
    endTime,
    pageSize: String(opts.pageSize || 50),
    orderBy: "start desc",
    view: "COMPLETE",
  };
  if (opts.filter) params.filter = opts.filter;

  const url = `${CLOUD_TRACE_V1}/projects/${projectId}/traces?${new URLSearchParams(params)}`;
  const resp = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!resp.ok) {
    const errText = await resp.text();
    console.error("Cloud Trace list error:", resp.status, errText);
    throw new Error(`Cloud Trace API error: ${resp.status}`);
  }

  const data = await resp.json();
  const traces: TraceListItem[] = [];

  for (const trace of data.traces || []) {
    const spans = trace.spans || [];
    if (spans.length === 0) continue;

    if (!isAgentTrace(spans)) continue;

    const rootSpan = spans.find((s: any) => !s.parentSpanId) || spans[0];
    const startMs = Math.min(...spans.map((s: any) => new Date(s.startTime).getTime()));
    const endMs = Math.max(...spans.map((s: any) => new Date(s.endTime).getTime()));

    const { orchestrator, subAgents, timings, subAgentIntervals } = analyzeAgentSpans(spans);

    const hasError = spans.some(
      (s: any) =>
        s.labels?.["otel.status_code"] === "ERROR" ||
        s.labels?.["agent.error"] ||
        s.labels?.["error"] === "true" ||
        s.labels?.["error"] === "1" ||
        s.labels?.["/error/message"] ||
        s.labels?.["exception.type"] ||
        s.labels?.["g.co/agent/error"] ||
        (s.labels?.["/http/status_code"] && parseInt(s.labels["/http/status_code"]) >= 400)
    );

    // Extract invocation ID from span labels
    const invocationId = extractInvocationId(spans);

    // Calculate net duration for the orchestrator (self-time excluding sub-agent time)
    // Use interval union to avoid double-counting overlapping/nested sub-agent spans
    const delegatedTime = computeIntervalUnion(subAgentIntervals);
    const netDuration = Math.max((endMs - startMs) - delegatedTime, 0);

    traces.push({
      traceId: trace.traceId,
      agentName: orchestrator,
      subAgents,
      startTime: rootSpan.startTime,
      duration: endMs - startMs,
      netDuration,
      spanCount: spans.length,
      hasError,
      agentTimings: timings,
      invocationId,
      subAgentIntervals,
    });
  }

  // Group sub-agent traces under the parent trace
  const grouped = groupChildTraces(traces);

  const stats = computeAgentStats(grouped);
  return { traces: grouped, stats };
}

export async function getTraceDetail(traceId: string): Promise<Trace> {
  const projectId = getProjectId();
  const token = await getAccessToken();

  const url = `${CLOUD_TRACE_V1}/projects/${projectId}/traces/${traceId}`;
  const resp = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!resp.ok) {
    const errText = await resp.text();
    console.error("Cloud Trace detail error:", resp.status, errText);
    throw new Error(`Cloud Trace API error: ${resp.status}`);
  }

  const data = await resp.json();
  const rawSpans = data.spans || [];
  const { orchestrator } = analyzeAgentSpans(rawSpans);

  const spans: TraceSpan[] = rawSpans.map((s: any) => ({
    spanId: s.spanId,
    name: s.name || "",
    parentSpanId: s.parentSpanId || undefined,
    startTime: s.startTime,
    endTime: s.endTime,
    status: s.labels?.["otel.status_code"]
      ? {
          code: s.labels["otel.status_code"] === "ERROR" ? 2 : 0,
          message: s.labels["otel.status_description"] || "",
        }
      : undefined,
    attributes: Object.fromEntries(
      Object.entries(s.labels || {}).map(([k, v]) => [
        k,
        { stringValue: String(v) },
      ])
    ),
    agentName: resolveSpanAgent(s, rawSpans, orchestrator),
  }));

  // Link orphan spans from sub-agent workloads to their parent spans
  linkCrossWorkloadSpans(spans);

  return { traceId, spans, projectId };
}

/**
 * Link orphan spans (from sub-agent workloads) under the correct parent.
 * When agent A calls agent B via transfer_to_agent/invoke_agent, agent B
 * runs in a separate reasoning engine with its own invocation span tree.
 * These spans have parentSpanId refs that don't exist in the main trace.
 * We match orphan root spans to invoke_agent/call_remote_agent spans by timing.
 */
function linkCrossWorkloadSpans(spans: TraceSpan[]): void {
  const byId = new Set(spans.map((s) => s.spanId));

  // Find orphan spans: have parentSpanId but parent doesn't exist in the trace
  const orphans = spans.filter(
    (s) => s.parentSpanId && !byId.has(s.parentSpanId)
  );
  if (orphans.length === 0) return;

  // Find potential parent spans: invoke_agent, call_remote_agent, execute_tool query_*, numbered spans
  const parentCandidates = spans.filter((s) =>
    s.name === "invoke_agent" ||
    s.name.startsWith("invoke_agent ") ||
    s.name.startsWith("call_remote_agent") ||
    /^execute_tool\s+query_/.test(s.name) ||
    /^\d+$/.test(s.name)
  );

  // Group orphans by their original parentSpanId (they share a common missing root)
  const orphanGroups = new Map<string, TraceSpan[]>();
  for (const o of orphans) {
    const pid = o.parentSpanId!;
    if (!orphanGroups.has(pid)) orphanGroups.set(pid, []);
    orphanGroups.get(pid)!.push(o);
  }

  // For each orphan group, find the best parent candidate by timing overlap
  for (const [missingPid, group] of orphanGroups.entries()) {
    // Find an orphan root: one whose name is "invocation" or has the earliest start
    const orphanRoot = group.find((s) => s.name === "invocation") ||
      group.sort((a, b) => new Date(a.startTime).getTime() - new Date(b.startTime).getTime())[0];

    if (!orphanRoot) continue;

    const oStart = new Date(orphanRoot.startTime).getTime();
    const oEnd = new Date(orphanRoot.endTime).getTime();

    let bestParent: TraceSpan | null = null;
    let bestOverlap = 0;

    for (const candidate of parentCandidates) {
      const cStart = new Date(candidate.startTime).getTime();
      const cEnd = new Date(candidate.endTime).getTime();

      // Check timing overlap
      const overlapStart = Math.max(oStart, cStart);
      const overlapEnd = Math.min(oEnd, cEnd);
      const overlap = Math.max(0, overlapEnd - overlapStart);

      if (overlap > bestOverlap) {
        bestOverlap = overlap;
        bestParent = candidate;
      }
    }

    if (bestParent) {
      // Reparent the orphan root under the best matching parent
      orphanRoot.parentSpanId = bestParent.spanId;
    } else {
      // No matching parent found; make it a true root
      orphanRoot.parentSpanId = undefined;
    }

    // Fix other orphans in the group: if they reference the same missing parent,
    // reparent them under the orphan root
    for (const o of group) {
      if (o === orphanRoot) continue;
      if (o.parentSpanId === missingPid) {
        o.parentSpanId = orphanRoot.spanId;
      }
    }
  }
}

function isAgentTrace(spans: any[]): boolean {
  return spans.some(
    (s) =>
      s.name === "invocation" ||
      s.name === "invoke_agent" ||
      /query_\w+_agent/.test(s.name)
  );
}

function computeIntervalUnion(intervals: [number, number][]): number {
  if (intervals.length === 0) return 0;
  const sorted = [...intervals].sort((a, b) => a[0] - b[0]);
  let total = 0;
  let [curStart, curEnd] = sorted[0];
  for (let i = 1; i < sorted.length; i++) {
    if (sorted[i][0] <= curEnd) {
      curEnd = Math.max(curEnd, sorted[i][1]);
    } else {
      total += curEnd - curStart;
      [curStart, curEnd] = sorted[i];
    }
  }
  total += curEnd - curStart;
  return total;
}

function analyzeAgentSpans(spans: any[]): {
  orchestrator: string;
  subAgents: string[];
  timings: Record<string, number>;
  subAgentIntervals: [number, number][];
} {
  let orchestrator = "SpendIQ";
  const subAgents: string[] = [];
  const timings: Record<string, number> = {};
  const subAgentIntervals: [number, number][] = [];

  const rootSpan = spans.find((s) => !s.parentSpanId) || spans[0];
  if (rootSpan) {
    const rootAgent =
      rootSpan.labels?.["g.co/agent/name"] ||
      rootSpan.labels?.["agent.name"] ||
      "";
    if (rootAgent) orchestrator = getAgentDisplayName(rootAgent);
  }

  const rootStart = rootSpan ? new Date(rootSpan.startTime).getTime() : 0;
  const rootEnd = rootSpan ? new Date(rootSpan.endTime).getTime() : 0;
  timings[orchestrator] = rootEnd - rootStart;

  for (const s of spans) {
    const name = s.name || "";
    const agentLabel = s.labels?.["g.co/agent/name"] || s.labels?.["agent.name"] || "";
    const durMs =
      new Date(s.endTime).getTime() - new Date(s.startTime).getTime();

    const queryMatch = name.match(/^query_(\w+?)(?:_agent)?$/);
    if (queryMatch) {
      const agentKey = queryMatch[1];
      const display = getAgentDisplayName(agentKey);
      if (!subAgents.includes(display)) subAgents.push(display);
      timings[display] = (timings[display] || 0) + durMs;
      continue;
    }

    if (name === "transfer_to_agent" && agentLabel) {
      const display = getAgentDisplayName(agentLabel);
      if (!subAgents.includes(display)) subAgents.push(display);
    }

    if (name === "invoke_agent" || name.startsWith("invoke_agent ")) {
      const resolvedAgent = agentLabel || name.replace(/^invoke_agent\s*/, "");
      if (resolvedAgent && resolvedAgent !== orchestrator) {
        const display = getAgentDisplayName(resolvedAgent);
        if (!subAgents.includes(display)) subAgents.push(display);
        timings[display] = Math.max(timings[display] || 0, durMs);
      }
    }

    if (name === "execute_tool" || name.startsWith("execute_tool ")) {
      const rawTool = agentLabel || name.replace(/^execute_tool\s*/, "") || "Tool";
      // Skip noise tool names that aren't user-meaningful
      if (
        rawTool === "transfer_to_agent" ||
        rawTool === "" ||
        rawTool === "Tool" ||
        rawTool === "(Merged)"
      ) continue;
      const display = rawTool.replace(/_/g, " ").replace(/\b\w/g, (ch: string) => ch.toUpperCase());
      if (!subAgents.includes(display)) subAgents.push(display);
      timings[display] = (timings[display] || 0) + durMs;
    }
  }

  // Filter out noise labels from subAgents
  const NOISE = new Set(["Transfer To Agent", "(Merged)", "Tool", "Call Llm", "LLM Call"]);
  const filteredSubAgents = subAgents.filter((s) => !NOISE.has(s));

  // Collect sub-agent intervals: any span whose agent label differs from orchestrator
  // is sub-agent work. The interval union handles nested/overlapping spans.
  for (const s of spans) {
    const label = s.labels?.["g.co/agent/name"] || s.labels?.["agent.name"] || "";
    if (label) {
      const display = getAgentDisplayName(label);
      if (display !== orchestrator) {
        subAgentIntervals.push([new Date(s.startTime).getTime(), new Date(s.endTime).getTime()]);
        continue;
      }
    }
    // Fallback: span name pattern for spans without agent labels
    const spanName = s.name || "";
    if (/^query_\w+(?:_agent)?$/.test(spanName)) {
      subAgentIntervals.push([new Date(s.startTime).getTime(), new Date(s.endTime).getTime()]);
    }
  }

  return { orchestrator, subAgents: filteredSubAgents, timings, subAgentIntervals };
}

function resolveSpanAgent(
  span: any,
  allSpans: any[],
  orchestrator: string
): string {
  const name = span.name || "";
  const agentLabel =
    span.labels?.["g.co/agent/name"] || span.labels?.["agent.name"] || "";

  if (agentLabel) return getAgentDisplayName(agentLabel);

  const queryMatch = name.match(/^query_(\w+?)(?:_agent)?$/);
  if (queryMatch) return getAgentDisplayName(queryMatch[1]);

  if (name === "invocation" || (name === "invoke_agent" && !span.parentSpanId))
    return orchestrator;

  if (span.parentSpanId) {
    const parent = allSpans.find((s: any) => s.spanId === span.parentSpanId);
    if (parent) return resolveSpanAgent(parent, allSpans, orchestrator);
  }

  return orchestrator;
}

function extractInvocationId(spans: any[]): string | undefined {
  for (const s of spans) {
    const labels = s.labels || {};
    // Agent Engine sets invocation/event IDs in labels
    const id =
      labels["gcp.vertex.agent_event_id"] ||
      labels["invocation_id"] ||
      labels["g.co/r/generic_task/job"] ||
      labels["session_id"];
    if (id) return id;
  }
  return undefined;
}

/**
 * Group sub-agent traces under their parent orchestrator trace.
 * A trace B is a child of trace A if:
 *   - B starts after A starts and ends before or near A's end
 *   - B's orchestrator is a known sub-agent of A
 */
function groupChildTraces(traces: TraceListItem[]): TraceListItem[] {
  if (traces.length <= 1) return traces;

  // Sort by duration desc so the longest (parent) trace comes first
  const sorted = [...traces].sort((a, b) => b.duration - a.duration);
  const absorbed = new Set<string>();

  for (let i = 0; i < sorted.length; i++) {
    if (absorbed.has(sorted[i].traceId)) continue;
    const parent = sorted[i];
    const pStart = new Date(parent.startTime).getTime();
    const pEnd = pStart + parent.duration;

    for (let j = 0; j < sorted.length; j++) {
      if (i === j || absorbed.has(sorted[j].traceId)) continue;
      const child = sorted[j];
      const cStart = new Date(child.startTime).getTime();
      const cEnd = cStart + child.duration;

      // Child must start within parent window (with 2s tolerance)
      // and end within parent window (with 5s tolerance for async cleanup)
      const startsWithin = cStart >= pStart - 2000;
      const endsWithin = cEnd <= pEnd + 5000;

      if (startsWithin && endsWithin) {
        // Absorb child into parent
        absorbed.add(child.traceId);

        // Add child's agent as a sub-agent if not already present
        if (!parent.subAgents.includes(child.agentName)) {
          parent.subAgents.push(child.agentName);
        }
        for (const sa of child.subAgents) {
          if (!parent.subAgents.includes(sa)) parent.subAgents.push(sa);
        }

        // Merge timings
        for (const [agent, ms] of Object.entries(child.agentTimings)) {
          parent.agentTimings[agent] = Math.max(parent.agentTimings[agent] || 0, ms);
        }

        // Track child trace IDs
        if (!parent.childTraceIds) parent.childTraceIds = [];
        parent.childTraceIds.push(child.traceId);

        // Add child trace as a sub-agent interval for accurate self-time
        if (!parent.subAgentIntervals) parent.subAgentIntervals = [];
        const cStartMs = new Date(child.startTime).getTime();
        parent.subAgentIntervals.push([cStartMs, cStartMs + child.duration]);

        // Aggregate span count
        parent.spanCount += child.spanCount;

        // Merge error status
        if (child.hasError) parent.hasError = true;
      }
    }

    // Recalculate net duration after merging children using interval union
    parent.netDuration = Math.max(
      parent.duration - computeIntervalUnion(parent.subAgentIntervals || []),
      0
    );
  }

  return sorted.filter((t) => !absorbed.has(t.traceId));
}

// Known agent names that are top-level agents (not subtasks)
const KNOWN_AGENTS = new Set([
  "SpendIQ", "Auditor", "Buyer", "Trend Analyst",
  "Supplier Classification", "Contract Intelligence",
  "Financial Leakage", "Visualization",
  "SQL Generation", "SQL Execution", "Validation",
]);

// Map subtask names to their parent agent
function getParentAgent(name: string): string | null {
  const lower = name.toLowerCase();
  // query_contract_intelligence → Contract Intelligence
  if (lower.includes("contract") && !KNOWN_AGENTS.has(name)) return "Contract Intelligence";
  if (lower.includes("cia") || lower.includes("retriever")) return "Contract Intelligence";
  if (lower.includes("graphrag")) return "Contract Intelligence";
  if (lower.includes("ssi") || lower.includes("execute sql")) return "Contract Intelligence";
  // Generic: if name starts with "Query " it's a subtask of the queried agent
  if (lower.startsWith("query ")) {
    const agentPart = name.replace(/^Query\s+/i, "").replace(/\s+Agent$/i, "");
    const match = [...KNOWN_AGENTS].find((a) => a.toLowerCase().includes(agentPart.toLowerCase()));
    if (match) return match;
  }
  return null;
}

function computeAgentStats(traces: TraceListItem[]): AgentStats[] {
  const agentData: Record<
    string,
    { durations: number[]; errors: number; isAgent: boolean }
  > = {};

  // Synthetic/noise labels that should never appear in Agent Performance
  const NOISE_LABELS = new Set(["Transfer To Agent", "(Merged)", "Call Llm", "LLM Call"]);

  for (const t of traces) {
    const name = t.agentName;
    if (!agentData[name]) agentData[name] = { durations: [], errors: 0, isAgent: true };
    // Use NET time for orchestrator (total - sub-agent time) to reflect own work
    agentData[name].durations.push(t.netDuration);
    if (t.hasError) agentData[name].errors++;

    // For sub-agents, compute their net time = gross - max(their own subtask timings)
    // The max approximates the dominant sub-task when sub-tasks run in parallel
    for (const sub of t.subAgents) {
      // Skip if sub is the same as orchestrator (prevents double-counting)
      if (sub === name) continue;
      if (NOISE_LABELS.has(sub)) continue;
      if (!agentData[sub]) agentData[sub] = { durations: [], errors: 0, isAgent: KNOWN_AGENTS.has(sub) };
      const gross = t.agentTimings[sub];
      if (gross) {
        // For sub-agents with identifiable subtasks, approximate net by subtracting max subtask
        // (wall-clock aware; handles parallel subtasks better than sum)
        const subSubtaskTimes = Object.entries(t.agentTimings)
          .filter(([n]) => n !== name && n !== sub && getParentAgent(n) === sub)
          .map(([, ms]) => ms);
        const maxChildTime = subSubtaskTimes.length > 0 ? Math.max(...subSubtaskTimes) : 0;
        const net = Math.max(gross - maxChildTime, 0);
        agentData[sub].durations.push(net);
      }
    }
  }

  function buildStat(agentName: string, data: { durations: number[]; errors: number; isAgent: boolean }): AgentStats {
    const sorted = [...data.durations].sort((a, b) => a - b);
    const avg = sorted.length > 0 ? sorted.reduce((a, b) => a + b, 0) / sorted.length : 0;
    const p90Idx = Math.floor(sorted.length * 0.9);
    return {
      agentName,
      avgDuration: Math.round(avg),
      requestCount: sorted.length,
      errorCount: data.errors,
      p90Duration: sorted[p90Idx] || 0,
      isAgent: data.isAgent,
      children: [],
    };
  }

  // Separate into top-level and children
  const topLevel: AgentStats[] = [];
  const childMap: Record<string, AgentStats[]> = {};

  for (const [name, data] of Object.entries(agentData)) {
    const parent = getParentAgent(name);
    if (parent && parent !== name) {
      if (!childMap[parent]) childMap[parent] = [];
      childMap[parent].push(buildStat(name, data));
    } else {
      topLevel.push(buildStat(name, data));
    }
  }

  // Attach children to their parent
  for (const stat of topLevel) {
    if (childMap[stat.agentName]) {
      stat.children = childMap[stat.agentName];
    }
  }

  return topLevel;
}
