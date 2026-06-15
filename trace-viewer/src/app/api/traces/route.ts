import { NextRequest, NextResponse } from "next/server";
import { listTraces } from "@/lib/cloud-trace";

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const startDate = searchParams.get("startDate") || undefined;
    const endDate = searchParams.get("endDate") || undefined;
    const minutes = startDate ? undefined : parseInt(searchParams.get("minutes") || "60", 10);
    const filter = searchParams.get("filter") || undefined;
    const pageSize = parseInt(searchParams.get("pageSize") || "50", 10);

    const { traces, stats } = await listTraces({
      startDate,
      endDate,
      minutes,
      pageSize,
      filter,
    });
    return NextResponse.json({ traces, stats });
  } catch (error: any) {
    console.error("Error listing traces:", error);
    return NextResponse.json(
      { error: error.message || "Failed to list traces" },
      { status: 500 }
    );
  }
}
