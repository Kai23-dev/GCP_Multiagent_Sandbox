import { NextRequest, NextResponse } from "next/server";
import { loadRegistry, saveRegistry, getStorageInfo, AgentRegistry } from "@/lib/agent-registry";

export async function GET() {
  try {
    const registry = await loadRegistry();
    const storage = getStorageInfo();
    return NextResponse.json({ registry, storage });
  } catch (err: any) {
    return NextResponse.json(
      { error: err.message || "Failed to load registry" },
      { status: 500 }
    );
  }
}

export async function PUT(req: NextRequest) {
  try {
    const body = (await req.json()) as AgentRegistry;
    if (!body || !Array.isArray(body.agents)) {
      return NextResponse.json({ error: "Invalid registry payload" }, { status: 400 });
    }
    // Basic sanitization: trim strings, drop empty keys
    body.agents = body.agents
      .map((a) => ({
        ...a,
        key: (a.key || "").trim(),
        displayName: (a.displayName || "").trim(),
        workloadId: (a.workloadId || "").trim(),
        resourceName: a.resourceName ? a.resourceName.trim() : undefined,
      }))
      .filter((a) => a.key && a.displayName);

    await saveRegistry(body);
    const storage = getStorageInfo();
    return NextResponse.json({
      ok: true,
      registry: body,
      storage,
    });
  } catch (err: any) {
    return NextResponse.json(
      { error: err.message || "Failed to save registry" },
      { status: 500 }
    );
  }
}
