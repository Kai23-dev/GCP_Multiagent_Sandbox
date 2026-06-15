import { NextRequest, NextResponse } from "next/server";
import { queryAgentLogs, queryLogsByServiceIds, extractConversation } from "@/lib/cloud-logging";

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const minutes = parseInt(searchParams.get("minutes") || "1440", 10);
    const agent = searchParams.get("agent") || undefined;
    const traceId = searchParams.get("traceId") || undefined;
    const pageSize = parseInt(searchParams.get("pageSize") || "200", 10);
    const serviceIds = searchParams.get("serviceIds") || undefined;
    const startTime = searchParams.get("startTime") || undefined;
    const endTime = searchParams.get("endTime") || undefined;

    // Primary query by trace ID or agent filter
    const primaryLogs = await queryAgentLogs(minutes, agent, traceId, pageSize);

    // If serviceIds provided, also query by those workloads in the time window
    let allLogs = primaryLogs;
    if (serviceIds && startTime && endTime) {
      const ids = serviceIds.split(",").filter(Boolean);
      // Only query services whose logs aren't already in the primary results
      const existingAgents = new Set(primaryLogs.map((l) => l.agentName));
      const missingIds = ids.filter((id) => !existingAgents.has(id));
      if (missingIds.length > 0) {
        const extraLogs = await queryLogsByServiceIds(
          missingIds,
          startTime,
          endTime,
          pageSize
        );
        allLogs = [...primaryLogs, ...extraLogs].sort(
          (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        );
      }
    }

    const conversation = traceId ? extractConversation(allLogs) : [];
    return NextResponse.json({ logs: allLogs, conversation });
  } catch (error: any) {
    console.error("Error querying logs:", error);
    return NextResponse.json(
      { error: error.message || "Failed to query logs" },
      { status: 500 }
    );
  }
}
