"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  RefreshCw,
  Search,
  Clock,
  AlertCircle,
  Activity,
  ChevronRight,
  ChevronDown,
  Zap,
  Filter,
  Calendar,
  BarChart3,
} from "lucide-react";

interface TraceListItem {
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
}

interface AgentStats {
  agentName: string;
  avgDuration: number;
  requestCount: number;
  errorCount: number;
  p90Duration: number;
  isAgent: boolean;
  children: AgentStats[];
}

type TimeMode = "relative" | "date";

const TIME_OPTIONS = [
  { label: "1h", value: 60 },
  { label: "6h", value: 360 },
  { label: "24h", value: 1440 },
  { label: "7d", value: 10080 },
];

function fmtDuration(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.round(ms)}ms`;
}

function fmtDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function DashboardPage() {
  const [traces, setTraces] = useState<TraceListItem[]>([]);
  const [stats, setStats] = useState<AgentStats[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timeMode, setTimeMode] = useState<TimeMode>("relative");
  const [timeRange, setTimeRange] = useState(1440);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [filterText, setFilterText] = useState("");
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);

  const fetchTraces = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ pageSize: "50" });
      if (timeMode === "date" && startDate) {
        params.set("startDate", startDate);
        if (endDate) params.set("endDate", endDate);
      } else {
        params.set("minutes", String(timeRange));
      }
      if (filterText) params.set("filter", filterText);

      const res = await fetch(`/api/traces?${params}`);
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setTraces(data.traces || []);
      setStats(data.stats || []);
    } catch (err: any) {
      setError(err.message);
      setTraces([]);
      setStats([]);
    } finally {
      setLoading(false);
    }
  }, [timeMode, timeRange, startDate, endDate, filterText]);

  useEffect(() => {
    fetchTraces();
  }, [fetchTraces]);

  const errorCount = traces.filter((t) => t.hasError).length;
  const avgDuration =
    traces.length > 0
      ? traces.reduce((sum, t) => sum + t.duration, 0) / traces.length
      : 0;
  const allAgentNames = new Set<string>();
  traces.forEach((t) => {
    allAgentNames.add(t.agentName);
    t.subAgents.forEach((sa) => allAgentNames.add(sa));
  });
  const uniqueAgents = allAgentNames.size;

  return (
    <div className="space-y-5">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          icon={<Activity className="w-5 h-5 text-blue-500" />}
          label="Total Requests"
          value={String(traces.length)}
        />
        <StatCard
          icon={<AlertCircle className="w-5 h-5 text-red-500" />}
          label="Errors"
          value={String(errorCount)}
          highlight={errorCount > 0}
        />
        <StatCard
          icon={<Clock className="w-5 h-5 text-amber-500" />}
          label="Avg Response Time"
          value={fmtDuration(avgDuration)}
        />
        <StatCard
          icon={<Zap className="w-5 h-5 text-emerald-500" />}
          label="Agents Active"
          value={String(uniqueAgents)}
        />
      </div>

      {/* Agent Performance */}
      {stats.length > 0 && (
        <div className="bg-white border rounded-lg shadow-sm p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
            <BarChart3 className="w-4 h-4" /> Agent Performance
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            {stats.map((s) => (
              <div key={s.agentName}>
                <div
                  className={`bg-gray-50 rounded-lg p-3 border transition-colors ${
                    s.children.length > 0 ? "cursor-pointer hover:border-brand-300" : ""
                  } ${expandedAgent === s.agentName ? "border-brand-400 ring-1 ring-brand-200" : ""}`}
                  onClick={() => s.children.length > 0 && setExpandedAgent(expandedAgent === s.agentName ? null : s.agentName)}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="text-xs font-semibold text-gray-800 truncate">
                      {s.agentName}
                    </div>
                    {s.children.length > 0 && (
                      expandedAgent === s.agentName
                        ? <ChevronDown className="w-3 h-3 text-gray-400 flex-shrink-0" />
                        : <ChevronRight className="w-3 h-3 text-gray-400 flex-shrink-0" />
                    )}
                  </div>
                  <div className="flex items-baseline gap-1">
                    <span className="text-lg font-bold text-gray-900">
                      {fmtDuration(s.avgDuration)}
                    </span>
                    <span className="text-[10px] text-gray-400" title="Self time: time spent in this agent excluding waiting on sub-agents">avg self</span>
                  </div>
                  <div className="flex gap-3 mt-1 text-[10px] text-gray-500">
                    <span>{s.requestCount} req</span>
                    <span>P90: {fmtDuration(s.p90Duration)}</span>
                    {s.errorCount > 0 && (
                      <span className="text-red-500">{s.errorCount} err</span>
                    )}
                  </div>
                  {s.children.length > 0 && (
                    <div className="text-[10px] text-brand-500 mt-1">
                      {s.children.length} subtask{s.children.length > 1 ? "s" : ""}
                    </div>
                  )}
                </div>
                {expandedAgent === s.agentName && s.children.length > 0 && (
                  <div className="mt-1 space-y-1 pl-2 border-l-2 border-brand-200">
                    {s.children.map((child) => (
                      <div key={child.agentName} className="bg-white rounded p-2 border text-[11px]">
                        <div className="font-semibold text-gray-700 truncate">{child.agentName}</div>
                        <div className="flex items-baseline gap-1 mt-0.5">
                          <span className="font-bold text-gray-800">{fmtDuration(child.avgDuration)}</span>
                          <span className="text-gray-400">avg</span>
                        </div>
                        <div className="flex gap-2 text-gray-400">
                          <span>{child.requestCount} req</span>
                          <span>P90: {fmtDuration(child.p90Duration)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Controls */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Time Mode Toggle */}
        <div className="flex items-center bg-white border rounded-lg overflow-hidden">
          <button
            onClick={() => setTimeMode("relative")}
            className={`px-2.5 py-1.5 text-xs font-medium transition-colors ${
              timeMode === "relative"
                ? "bg-brand-600 text-white"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            Recent
          </button>
          <button
            onClick={() => setTimeMode("date")}
            className={`px-2.5 py-1.5 text-xs font-medium transition-colors flex items-center gap-1 ${
              timeMode === "date"
                ? "bg-brand-600 text-white"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            <Calendar className="w-3 h-3" />
            Date
          </button>
        </div>

        {timeMode === "relative" ? (
          <div className="flex items-center bg-white border rounded-lg overflow-hidden">
            {TIME_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setTimeRange(opt.value)}
                className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                  timeRange === opt.value
                    ? "bg-brand-600 text-white"
                    : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        ) : (
          <div className="flex items-center gap-2">
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
        )}

        <div className="relative flex-1 max-w-sm">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Filter by agent name..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && fetchTraces()}
            className="w-full pl-9 pr-3 py-1.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        <button
          onClick={fetchTraces}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Trace List */}
      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              <th className="px-4 py-3 w-10">Status</th>
              <th className="px-4 py-3">Agent</th>
              <th className="px-4 py-3">Sub-Agents</th>
              <th className="px-4 py-3">Total</th>
              <th className="px-4 py-3">Steps</th>
              <th className="px-4 py-3">Date</th>
              <th className="px-4 py-3">Time</th>
              <th className="px-4 py-3 w-8"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading && traces.length === 0 ? (
              <tr>
                <td
                  colSpan={8}
                  className="px-4 py-12 text-center text-gray-400"
                >
                  <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2" />
                  Loading...
                </td>
              </tr>
            ) : traces.length === 0 ? (
              <tr>
                <td
                  colSpan={8}
                  className="px-4 py-12 text-center text-gray-400"
                >
                  <Search className="w-5 h-5 mx-auto mb-2" />
                  No agent requests found for the selected time range.
                </td>
              </tr>
            ) : (
              traces.map((trace) => (
                <tr
                  key={trace.traceId}
                  className="hover:bg-blue-50 transition-colors cursor-pointer"
                >
                  <td className="px-4 py-2.5">
                    <div
                      className={`w-2.5 h-2.5 rounded-full ${
                        trace.hasError ? "bg-red-500" : "bg-emerald-500"
                      }`}
                    />
                  </td>
                  <td className="px-4 py-2.5">
                    <Link
                      href={`/trace/${trace.traceId}`}
                      className="text-sm font-semibold text-brand-700 hover:underline"
                    >
                      {trace.agentName}
                    </Link>
                    {trace.invocationId && (
                      <div className="text-[10px] text-gray-400 font-mono truncate max-w-[180px]" title={trace.invocationId}>
                        {trace.invocationId.slice(0, 20)}...
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex flex-wrap gap-1">
                      {trace.subAgents.map((sa) => (
                        <span
                          key={sa}
                          className="px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded text-[11px] font-medium"
                        >
                          {sa}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`text-sm font-semibold ${
                        trace.duration > 15000
                          ? "text-red-600"
                          : trace.duration > 8000
                          ? "text-amber-600"
                          : "text-gray-700"
                      }`}
                    >
                      {fmtDuration(trace.duration)}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="text-sm text-gray-500">
                      {trace.spanCount}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="text-xs text-gray-500">
                      {fmtDate(trace.startTime)}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="text-xs text-gray-400">
                      {fmtTime(trace.startTime)}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <Link href={`/trace/${trace.traceId}`}>
                      <ChevronRight className="w-4 h-4 text-gray-400" />
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  highlight,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`bg-white border rounded-lg p-4 flex items-center gap-3 ${
        highlight ? "border-red-200 bg-red-50" : ""
      }`}
    >
      {icon}
      <div>
        <div className="text-2xl font-bold text-gray-900">{value}</div>
        <div className="text-xs text-gray-500">{label}</div>
      </div>
    </div>
  );
}
