import { NextRequest, NextResponse } from "next/server";
import { getTraceDetail } from "@/lib/cloud-trace";
import { queryAgentLogs, queryLogsByServiceIds, buildTimelineFromLogs } from "@/lib/cloud-logging";
import { loadRegistry, findWorkloadId } from "@/lib/agent-registry";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ traceId: string }> }
) {
  try {
    const { traceId } = await params;

    // Fetch Cloud Trace spans and logs in parallel
    const [trace, logs] = await Promise.all([
      getTraceDetail(traceId),
      queryAgentLogs(10080, undefined, traceId, 200),
    ]);

    // Build timeline spans from logs
    const timelineSpans = buildTimelineFromLogs(logs);

    // Check if Cloud Trace has spans from multiple services (cross-workload)
    const serviceNames = new Set<string>();
    for (const s of trace.spans) {
      const svc = s.attributes?.["service.name"]?.stringValue;
      if (svc) serviceNames.add(svc);
    }
    const isMultiWorkload = serviceNames.size > 1;

    // Prefer Cloud Trace spans when we have multi-workload data
    // Only use timeline spans if Cloud Trace is truly incomplete (single workload, fewer spans)
    if (!isMultiWorkload && timelineSpans.length > 1) {
      const traceMs = trace.spans.length > 0
        ? Math.max(...trace.spans.map((s) => new Date(s.endTime).getTime())) -
          Math.min(...trace.spans.map((s) => new Date(s.startTime).getTime()))
        : 0;
      const timelineMs =
        Math.max(...timelineSpans.map((s) => new Date(s.endTime).getTime())) -
        Math.min(...timelineSpans.map((s) => new Date(s.startTime).getTime()));

      const timelineAgentCount = timelineSpans.filter(
        (s) => s.parentSpanId && s.name !== "call_llm"
      ).length;
      const traceAgentCount = trace.spans.filter(
        (s) =>
          s.name.startsWith("invoke_agent") ||
          s.name.startsWith("execute_tool") ||
          s.name.startsWith("query_")
      ).length;

      const useTimeline =
        timelineMs > traceMs * 1.5 || timelineAgentCount > traceAgentCount;

      if (useTimeline) {
        trace.spans = timelineSpans.map((ts) => ({
          spanId: ts.spanId,
          name: ts.name,
          parentSpanId: ts.parentSpanId,
          startTime: ts.startTime,
          endTime: ts.endTime,
          agentName: ts.agentName,
          attributes: {},
        }));
      }
    }

    // Load agent registry and enrich with cross-workload sub-agent data
    const registry = await loadRegistry();

    // Detect sub-agent references in spans (transfer_to_agent args, query_*_agent names, invoke_agent names)
    const referencedAgentKeys = new Set<string>();
    for (const s of trace.spans) {
      // Patterns: "invoke_agent contract_intelligence_agent", "query_contract_intelligence_agent"
      const name = s.name || "";
      const invokeMatch = name.match(/^invoke_agent\s+(\w+)/);
      if (invokeMatch) referencedAgentKeys.add(invokeMatch[1]);
      const queryMatch = name.match(/^(?:execute_tool\s+)?query_(\w+?)(?:_agent)?$/);
      if (queryMatch) referencedAgentKeys.add(queryMatch[1] + "_agent");

      // transfer_to_agent typically has agent_name in labels/attributes
      const agentNameAttr = s.attributes?.["gcp.vertex.agent.agent_name"]?.stringValue ||
        s.attributes?.["agent.name"]?.stringValue ||
        s.attributes?.["tool.args"]?.stringValue;
      if (agentNameAttr) {
        const m = agentNameAttr.match(/"agent_name"\s*:\s*"([^"]+)"/);
        if (m) referencedAgentKeys.add(m[1]);
        else if (/^\w+_agent$/.test(agentNameAttr)) referencedAgentKeys.add(agentNameAttr);
      }
    }

    // Resolve referenced agents to workload IDs via registry
    const subWorkloadIds = new Set<string>();
    for (const key of referencedAgentKeys) {
      const wid = findWorkloadId(registry, key);
      if (wid) subWorkloadIds.add(wid);
    }

    // Also collect workloads already present in the spans
    const existingWorkloads = new Set<string>();
    for (const s of trace.spans) {
      const svc = s.attributes?.["service.name"]?.stringValue;
      if (svc) existingWorkloads.add(svc);
    }

    // Only query workloads not already present
    const missingWorkloads = [...subWorkloadIds].filter((w) => !existingWorkloads.has(w));

    if (missingWorkloads.length > 0 && trace.spans.length > 0) {
      const starts = trace.spans.map((s) => new Date(s.startTime).getTime());
      const ends = trace.spans.map((s) => new Date(s.endTime).getTime());
      const windowStart = new Date(Math.min(...starts) - 60000).toISOString();
      const windowEnd = new Date(Math.max(...ends) + 60000).toISOString();

      // Build reverse map: workloadId -> agent display name (from registry)
      const workloadToAgent = new Map<string, string>();
      for (const a of registry.agents) {
        if (a.workloadId) workloadToAgent.set(a.workloadId, a.displayName);
      }

      // Find candidate parent spans in the primary trace
      const parentCandidates = trace.spans.filter(
        (s) =>
          s.name === "invoke_agent" ||
          s.name.startsWith("invoke_agent ") ||
          s.name.startsWith("call_remote_agent") ||
          /^execute_tool\s+query_/.test(s.name) ||
          /query_\w+_agent/.test(s.name)
      );

      try {
        // Query each missing workload separately so we can tag spans with the correct agent
        const allSubSpans: Array<{
          spanId: string;
          name: string;
          parentSpanId?: string;
          startTime: string;
          endTime: string;
          agentName: string;
          workloadId: string;
        }> = [];

        await Promise.all(
          missingWorkloads.map(async (wid) => {
            const agentHint = workloadToAgent.get(wid);
            const logs = await queryLogsByServiceIds([wid], windowStart, windowEnd, 500);
            const spans = buildTimelineFromLogs(logs, agentHint);
            // Prefix spanIds to avoid collisions across workloads
            const prefix = `w${wid}_`;
            for (const s of spans) {
              allSubSpans.push({
                spanId: prefix + s.spanId,
                name: s.name,
                parentSpanId: s.parentSpanId ? prefix + s.parentSpanId : undefined,
                startTime: s.startTime,
                endTime: s.endTime,
                agentName: s.agentName || agentHint || "Unknown",
                workloadId: wid,
              });
            }
          })
        );

        if (allSubSpans.length > 0) {
          // Find root spans (parent not in the sub-span set)
          const subIds = new Set(allSubSpans.map((s) => s.spanId));
          const rootSubSpans = allSubSpans.filter(
            (s) => !s.parentSpanId || !subIds.has(s.parentSpanId)
          );

          // Attach each sub-agent's root span to the best primary parent by timing overlap
          for (const root of rootSubSpans) {
            const rStart = new Date(root.startTime).getTime();
            const rEnd = new Date(root.endTime).getTime();
            let best: (typeof parentCandidates)[number] | null = null;
            let bestOverlap = 0;
            for (const c of parentCandidates) {
              const cStart = new Date(c.startTime).getTime();
              const cEnd = new Date(c.endTime).getTime();
              const overlap = Math.max(0, Math.min(rEnd, cEnd) - Math.max(rStart, cStart));
              if (overlap > bestOverlap) {
                bestOverlap = overlap;
                best = c;
              }
            }
            if (best) {
              root.parentSpanId = best.spanId;
            }
          }

          // Merge sub-agent synthetic spans into the main trace
          trace.spans = [
            ...trace.spans,
            ...allSubSpans.map((ts) => ({
              spanId: ts.spanId,
              name: ts.name,
              parentSpanId: ts.parentSpanId,
              startTime: ts.startTime,
              endTime: ts.endTime,
              agentName: ts.agentName,
              attributes: {
                "service.name": { stringValue: ts.workloadId },
                "synthetic.source": { stringValue: "logs" },
              } as Record<string, { stringValue?: string }>,
            })),
          ];
        }
      } catch (e) {
        console.warn("Sub-agent log enrichment failed:", e);
      }
    }

    return NextResponse.json(trace);
  } catch (error: any) {
    console.error("Error getting trace:", error);
    return NextResponse.json(
      { error: error.message || "Failed to get trace" },
      { status: 500 }
    );
  }
}
