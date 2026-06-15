"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import {
  RefreshCw,
  Calendar,
  TrendingUp,
  Clock,
  AlertCircle,
  BarChart3,
} from "lucide-react";
import GroupedBarChart from "@/components/charts/GroupedBarChart";

interface TraceListItem {
  traceId: string;
  agentName: string;
  subAgents: string[];
  startTime: string;
  duration: number;
  spanCount: number;
  hasError: boolean;
  agentTimings: Record<string, number>;
}

interface DailyAgentData {
  date: string;
  agents: Record<
    string,
    { count: number; totalDuration: number; errors: number }
  >;
}

function fmtDuration(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.round(ms)}ms`;
}

function getDateKey(iso: string): string {
  return new Date(iso).toISOString().slice(0, 10);
}

function buildDailyData(traces: TraceListItem[]): DailyAgentData[] {
  const dayMap: Record<
    string,
    Record<string, { count: number; totalDuration: number; errors: number }>
  > = {};

  for (const t of traces) {
    const date = getDateKey(t.startTime);
    if (!dayMap[date]) dayMap[date] = {};

    const agents = [t.agentName, ...t.subAgents];
    for (const agent of agents) {
      if (!dayMap[date][agent])
        dayMap[date][agent] = { count: 0, totalDuration: 0, errors: 0 };
      dayMap[date][agent].count++;
      dayMap[date][agent].totalDuration +=
        t.agentTimings[agent] || t.duration;
      if (t.hasError) dayMap[date][agent].errors++;
    }
  }

  return Object.entries(dayMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, agents]) => ({ date, agents }));
}

const AGENT_COLORS: Record<string, string> = {
  SpendIQ: "#2563eb",
  Auditor: "#10b981",
  Buyer: "#8b5cf6",
  "Trend Analyst": "#f59e0b",
  "Supplier Classification": "#f43f5e",
  "Contract Intelligence": "#06b6d4",
  "Financial Leakage": "#f97316",
  Visualization: "#6366f1",
  "SQL Generation": "#14b8a6",
  Validation: "#84cc16",
  "SQL Execution": "#0ea5e9",
};

function getColor(agent: string): string {
  return AGENT_COLORS[agent] || "#9ca3af";
}

export default function TrendsPage() {
  const [traces, setTraces] = useState<TraceListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 7);
    return d.toISOString().slice(0, 10);
  });
  const [endDate, setEndDate] = useState(
    () => new Date().toISOString().slice(0, 10)
  );

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        startDate,
        endDate,
        pageSize: "200",
      });
      const res = await fetch(`/api/traces?${params}`);
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setTraces(data.traces || []);
    } catch (err: any) {
      setError(err.message);
      setTraces([]);
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const dailyData = buildDailyData(traces);

  // Rank agents by total request count and take top 8 for readable charts
  const topAgents = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const d of dailyData) {
      for (const [agent, data] of Object.entries(d.agents)) {
        counts[agent] = (counts[agent] || 0) + data.count;
      }
    }
    return Object.entries(counts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 8)
      .map(([agent]) => agent);
  }, [dailyData]);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-brand-600" />
          Agent Trends
        </h2>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-gray-400" />
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="px-2.5 py-1.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
            <span className="text-gray-400 text-sm">to</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="px-2.5 py-1.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 disabled:opacity-50"
          >
            <RefreshCw
              className={`w-4 h-4 ${loading ? "animate-spin" : ""}`}
            />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* Legend */}
      {topAgents.length > 0 && (
        <div className="flex flex-wrap gap-3">
          {topAgents.map((agent) => (
            <div key={agent} className="flex items-center gap-1.5 text-xs">
              <div
                className="w-3 h-3 rounded-sm"
                style={{ backgroundColor: getColor(agent) }}
              />
              <span className="text-gray-600 font-medium">{agent}</span>
            </div>
          ))}
        </div>
      )}

      {/* Requests per Day - Bar Chart */}
      <div className="bg-white border rounded-lg shadow-sm p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-1.5">
          <BarChart3 className="w-4 h-4" /> Requests per Day by Agent
          <span className="ml-2 text-[10px] font-normal text-gray-400">(top 8 agents)</span>
        </h3>
        {dailyData.length === 0 ? (
          <div className="text-center py-12 text-gray-400 text-sm">
            No data for the selected date range.
          </div>
        ) : (
          <GroupedBarChart
            groups={dailyData.map((d) => ({
              label: d.date.slice(5),
              values: topAgents.map((agent) => ({
                name: agent,
                color: getColor(agent),
                value: d.agents[agent]?.count || 0,
              })),
            }))}
            yLabel="Requests"
            yFormatter={(v) => String(Math.round(v))}
          />
        )}
      </div>

      {/* Avg Response Time - Grouped Bar Chart */}
      <div className="bg-white border rounded-lg shadow-sm p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-1.5">
          <BarChart3 className="w-4 h-4" /> Avg Response Time per Day by Agent
          <span className="ml-2 text-[10px] font-normal text-gray-400">(top 8 agents)</span>
        </h3>
        {dailyData.length === 0 ? (
          <div className="text-center py-12 text-gray-400 text-sm">
            No data for the selected date range.
          </div>
        ) : (
          <GroupedBarChart
            groups={dailyData.map((d) => ({
              label: d.date.slice(5),
              values: topAgents.map((agent) => ({
                name: agent,
                color: getColor(agent),
                value: d.agents[agent]
                  ? d.agents[agent].totalDuration / d.agents[agent].count
                  : 0,
              })),
            }))}
            yLabel="Duration"
            yFormatter={fmtDuration}
          />
        )}
      </div>
    </div>
  );
}
