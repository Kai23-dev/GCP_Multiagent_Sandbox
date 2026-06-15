import { getAccessToken, getProjectId } from "./gcp-auth";
import { getAgentDisplayName } from "./cloud-trace";

export interface LogEntry {
  timestamp: string;
  severity: string;
  agentName: string;
  message: string;
  traceId?: string;
  spanId?: string;
  labels?: Record<string, string>;
  jsonPayload?: Record<string, unknown>;
  eventType?: string;
}

export interface ConversationTurn {
  role: "user" | "agent";
  agentName: string;
  text: string;
  timestamp: string;
  toolCall?: { name: string; args: Record<string, unknown> };
}

const LOGGING_BASE = "https://logging.googleapis.com/v2";

const PREFIX_MAP: Record<string, string> = {
  bu: "buyer_agent",
  ta: "trend_agent",
  sc: "supplier_classification_agent",
  fl: "financial_leakage_agent",
  vi: "visualization_agent",
  au: "auditor_agent",
  sp: "spend_iq_agent",
  co: "contract_intelligence_agent",
  sg: "sql_generation_agent",
  se: "sql_execution_agent",
  va: "validation_agent",
};

export async function queryAgentLogs(
  timeRangeMinutes: number = 60,
  agentFilter?: string,
  traceId?: string,
  pageSize: number = 200
): Promise<LogEntry[]> {
  const projectId = getProjectId();
  const token = await getAccessToken();

  const endTime = new Date().toISOString();
  const startTime = new Date(
    Date.now() - timeRangeMinutes * 60 * 1000
  ).toISOString();

  let filter = `resource.type="aiplatform.googleapis.com/ReasoningEngine"`;
  filter += ` AND timestamp>="${startTime}" AND timestamp<="${endTime}"`;

  if (traceId) {
    filter += ` AND trace="projects/${projectId}/traces/${traceId}"`;
  }

  if (agentFilter) {
    filter += ` AND textPayload:("${agentFilter}")`;
  }

  const url = `${LOGGING_BASE}/entries:list`;
  const resp = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      resourceNames: [`projects/${projectId}`],
      filter,
      orderBy: "timestamp asc",
      pageSize,
    }),
  });

  if (!resp.ok) {
    const errText = await resp.text();
    console.error("Cloud Logging error:", resp.status, errText);
    throw new Error(`Cloud Logging API error: ${resp.status}`);
  }

  const data = await resp.json();
  const entries: LogEntry[] = [];

  for (const entry of data.entries || []) {
    const agentName = extractAgentName(entry);
    const message =
      entry.textPayload ||
      entry.jsonPayload?.message ||
      JSON.stringify(entry.jsonPayload || {});

    entries.push({
      timestamp: entry.timestamp,
      severity: entry.severity || "DEFAULT",
      agentName,
      message: String(message),
      traceId: entry.trace ? entry.trace.split("/").pop() : undefined,
      spanId: entry.spanId,
      labels: entry.labels,
      jsonPayload: entry.jsonPayload,
      eventType: entry.labels?.["event.name"] || undefined,
    });
  }

  return entries;
}

export function extractConversation(logs: LogEntry[]): ConversationTurn[] {
  const turns: ConversationTurn[] = [];

  for (const log of logs) {
    const eventName = log.eventType;
    const payload = log.jsonPayload as any;
    if (!payload?.content) continue;

    if (eventName === "gen_ai.user.message") {
      const parts = payload.content?.parts || [];
      const textParts = parts
        .map((p: any) => p?.text)
        .filter((t: string) => t && !t.startsWith("For context:") && !t.startsWith("["));
      if (textParts.length > 0) {
        turns.push({
          role: "user",
          agentName: log.agentName,
          text: textParts.join("\n"),
          timestamp: log.timestamp,
        });
      }
    }

    if (eventName === "gen_ai.choice") {
      const parts = payload.content?.parts || [];
      for (const part of parts) {
        if (part?.text) {
          turns.push({
            role: "agent",
            agentName: log.agentName,
            text: part.text,
            timestamp: log.timestamp,
          });
        }
        if (part?.function_call) {
          const fc = part.function_call;
          turns.push({
            role: "agent",
            agentName: log.agentName,
            text: `Called ${fc.name}`,
            timestamp: log.timestamp,
            toolCall: { name: fc.name, args: fc.args || {} },
          });
        }
      }
    }
  }

  return turns;
}

export interface TimelineSpan {
  spanId: string;
  name: string;
  parentSpanId?: string;
  startTime: string;
  endTime: string;
  agentName: string;
}

export function buildTimelineFromLogs(logs: LogEntry[], orchestratorHint?: string): TimelineSpan[] {
  if (logs.length === 0) return [];

  const traced = logs.filter((l) => l.eventType);
  if (traced.length === 0) return [];

  // Detect orchestrator name from first system message (or use hint if provided)
  let orchestratorName = orchestratorHint || "Unknown";
  if (!orchestratorHint) {
    for (const log of traced) {
      if (log.eventType === "gen_ai.system.message") {
        const payload = (log.jsonPayload as any)?.content;
        let sysText = "";
        if (typeof payload === "string") {
          sysText = payload;
        } else if (payload?.parts) {
          sysText = (payload.parts as any[]).map((p: any) => p?.text || "").join(" ");
        }
        if (sysText) {
          const lower = sysText.toLowerCase();
          if (lower.includes("spend iq") || lower.includes("spend_iq") || lower.includes("spendiq")) { orchestratorName = "SpendIQ"; break; }
          if (lower.includes("contract intelligence") || lower.includes("contract_intelligence")) { orchestratorName = "Contract Intelligence"; break; }
          if (lower.includes("auditor")) { orchestratorName = "Auditor"; break; }
          if (lower.includes("buyer")) { orchestratorName = "Buyer"; break; }
          if (lower.includes("trend")) { orchestratorName = "Trend Analyst"; break; }
          if (lower.includes("financial leakage") || lower.includes("financial_leakage")) { orchestratorName = "Financial Leakage"; break; }
          if (lower.includes("supplier classification") || lower.includes("supplier_classification")) { orchestratorName = "Supplier Classification"; break; }
          if (lower.includes("visualization")) { orchestratorName = "Visualization"; break; }
          if (lower.includes("sql generation") || lower.includes("sql_generation")) { orchestratorName = "SQL Generation"; break; }
          if (lower.includes("validation")) { orchestratorName = "Validation"; break; }
          if (lower.includes("sql execution") || lower.includes("sql_execution")) { orchestratorName = "SQL Execution"; break; }
        }
        break;
      }
    }
  }

  // Find invocation time window
  let invocationStart = traced[0].timestamp;
  const invocationEnd = traced[traced.length - 1].timestamp;

  for (const log of traced) {
    if (log.eventType === "gen_ai.user.message") {
      const parts = (log.jsonPayload as any)?.content?.parts || [];
      const hasRealUser = parts.some(
        (p: any) =>
          p?.text &&
          !p.text.startsWith("For context:") &&
          !p.text.startsWith("[")
      );
      if (hasRealUser) {
        invocationStart = log.timestamp;
        break;
      }
    }
  }

  const spans: TimelineSpan[] = [];
  const rootId = "tl_root";
  spans.push({
    spanId: rootId,
    name: "invocation",
    startTime: invocationStart,
    endTime: invocationEnd,
    agentName: orchestratorName,
  });

  // Track pending tool calls
  interface PendingCall {
    startTs: string;
    toolName: string;
  }
  const pending: PendingCall[] = [];
  let idx = 0;

  // Track transfer_to_agent for sub-agent grouping
  let activeTransfer: { spanId: string; agent: string; startTs: string } | null = null;

  for (const log of traced) {
    const parts = (log.jsonPayload as any)?.content?.parts || [];

    if (log.eventType === "gen_ai.choice") {
      for (const part of parts) {
        if (!part?.function_call) continue;
        const fc = part.function_call;
        const name: string = fc.name || "";

        if (name === "transfer_to_agent") {
          // Close previous transfer if any
          if (activeTransfer) {
            const existing = spans.find((s) => s.spanId === activeTransfer!.spanId);
            if (existing) existing.endTime = log.timestamp;
          }
          idx++;
          const targetAgent = fc.args?.agent_name || "unknown";
          const transferSpanId = `tl_transfer_${idx}`;
          spans.push({
            spanId: transferSpanId,
            name: `transfer_to_agent`,
            parentSpanId: rootId,
            startTime: log.timestamp,
            endTime: invocationEnd, // will be closed later
            agentName: getAgentDisplayName(targetAgent),
          });
          activeTransfer = {
            spanId: transferSpanId,
            agent: targetAgent,
            startTs: log.timestamp,
          };
        } else {
          // Regular tool/agent call
          pending.push({ startTs: log.timestamp, toolName: name });
        }
      }
    }

    if (log.eventType === "gen_ai.user.message") {
      for (const part of parts) {
        const text: string = part?.text || "";
        // Match: [agent] `tool_name` tool returned result
        const returnMatch = text.match(
          /\[\w+\]\s+`(\w+)`\s+tool returned result/
        );
        if (returnMatch) {
          const toolName = returnMatch[1];
          if (toolName === "transfer_to_agent") continue; // skip transfer results

          const callIdx = pending.findIndex((p) => p.toolName === toolName);
          if (callIdx >= 0) {
            const call = pending.splice(callIdx, 1)[0];
            idx++;
            const agentKey = toolName
              .replace(/^query_/, "")
              .replace(/_agent$/, "");
            const parentId = activeTransfer ? activeTransfer.spanId : rootId;
            spans.push({
              spanId: `tl_tool_${idx}`,
              name: toolName,
              parentSpanId: parentId,
              startTime: call.startTs,
              endTime: log.timestamp,
              agentName: getAgentDisplayName(agentKey),
            });

            // Update the transfer span's end time
            if (activeTransfer) {
              const transferSpan = spans.find(
                (s) => s.spanId === activeTransfer!.spanId
              );
              if (
                transferSpan &&
                new Date(log.timestamp) > new Date(transferSpan.endTime)
              ) {
                transferSpan.endTime = log.timestamp;
              }
            }
          }
        }
      }
    }
  }

  // Close unclosed pending calls
  for (const call of pending) {
    idx++;
    const agentKey = call.toolName
      .replace(/^query_/, "")
      .replace(/_agent$/, "");
    const parentId = activeTransfer ? activeTransfer.spanId : rootId;
    spans.push({
      spanId: `tl_unclosed_${idx}`,
      name: call.toolName,
      parentSpanId: parentId,
      startTime: call.startTs,
      endTime: invocationEnd,
      agentName: getAgentDisplayName(agentKey),
    });
  }

  // Add LLM call spans between events (first user msg → first tool call)
  const firstToolCallTs = spans
    .filter((s) => s.spanId !== rootId && !s.spanId.startsWith("tl_transfer"))
    .map((s) => new Date(s.startTime).getTime())
    .sort((a, b) => a - b)[0];

  if (firstToolCallTs) {
    const llmDur = firstToolCallTs - new Date(invocationStart).getTime();
    if (llmDur > 500) {
      idx++;
      spans.push({
        spanId: `tl_llm_${idx}`,
        name: "call_llm",
        parentSpanId: rootId,
        startTime: invocationStart,
        endTime: new Date(firstToolCallTs).toISOString(),
        agentName: orchestratorName,
      });
    }
  }

  return spans;
}

export async function queryLogsByServiceIds(
  serviceIds: string[],
  startTime: string,
  endTime: string,
  pageSize: number = 200
): Promise<LogEntry[]> {
  if (serviceIds.length === 0) return [];
  const projectId = getProjectId();
  const token = await getAccessToken();

  const idFilter = serviceIds
    .map((id) => `resource.labels.reasoning_engine_id="${id}"`)
    .join(" OR ");

  const filter = `resource.type="aiplatform.googleapis.com/ReasoningEngine"` +
    ` AND (${idFilter})` +
    ` AND timestamp>="${startTime}" AND timestamp<="${endTime}"`;

  const url = `${LOGGING_BASE}/entries:list`;
  const resp = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      resourceNames: [`projects/${projectId}`],
      filter,
      orderBy: "timestamp asc",
      pageSize,
    }),
  });

  if (!resp.ok) {
    console.error("Cloud Logging (by service) error:", resp.status);
    return [];
  }

  const data = await resp.json();
  const entries: LogEntry[] = [];

  for (const entry of data.entries || []) {
    const agentName = extractAgentName(entry);
    const message =
      entry.textPayload ||
      entry.jsonPayload?.message ||
      JSON.stringify(entry.jsonPayload || {});

    entries.push({
      timestamp: entry.timestamp,
      severity: entry.severity || "DEFAULT",
      agentName,
      message: String(message),
      traceId: entry.trace ? entry.trace.split("/").pop() : undefined,
      spanId: entry.spanId,
      labels: entry.labels,
      jsonPayload: entry.jsonPayload,
      eventType: entry.labels?.["event.name"] || undefined,
    });
  }

  return entries;
}

function extractAgentName(entry: any): string {
  const resourceLabels = entry.resource?.labels || {};
  const text = entry.textPayload || "";
  const prefixMatch = text.match(/^(\w{2})=====/)
  if (prefixMatch) {
    const agent = PREFIX_MAP[prefixMatch[1]];
    if (agent) return getAgentDisplayName(agent);
  }

  if (resourceLabels.reasoning_engine_id) {
    return resourceLabels.reasoning_engine_id;
  }

  return "unknown";
}
