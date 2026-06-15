"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  RefreshCw,
  ExternalLink,
  AlertCircle,
  MessageSquare,
  User,
  Bot,
  Wrench,
  GitBranch,
} from "lucide-react";
import TraceWaterfall from "@/components/TraceWaterfall";
import ProcessMap from "@/components/ProcessMap";
import SpanDetail from "@/components/SpanDetail";

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

interface LogEntry {
  timestamp: string;
  severity: string;
  agentName: string;
  message: string;
  traceId?: string;
  spanId?: string;
}

interface ConversationTurn {
  role: "user" | "agent";
  agentName: string;
  text: string;
  timestamp: string;
  toolCall?: { name: string; args: Record<string, unknown> };
}

export default function TraceDetailPage() {
  const params = useParams();
  const traceId = params.traceId as string;
  const [spans, setSpans] = useState<Span[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [conversation, setConversation] = useState<ConversationTurn[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSpan, setSelectedSpan] = useState<Span | null>(null);
  const [activeTab, setActiveTab] = useState<
    "waterfall" | "conversation" | "logs" | "processmap"
  >("waterfall");

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        // First fetch trace spans
        const traceRes = await fetch(`/api/traces/${traceId}`);

        if (!traceRes.ok) {
          const err = await traceRes.json();
          throw new Error(err.error || `Trace API error: ${traceRes.status}`);
        }

        const traceData = await traceRes.json();
        const traceSpans: Span[] = traceData.spans || [];
        setSpans(traceSpans);

        // Extract service IDs from spans to query all workload logs
        const serviceIds = new Set<string>();
        let traceStart = "";
        let traceEnd = "";
        if (traceSpans.length > 0) {
          const starts = traceSpans.map((s) => new Date(s.startTime).getTime());
          const ends = traceSpans.map((s) => new Date(s.endTime).getTime());
          traceStart = new Date(Math.min(...starts) - 60000).toISOString();
          traceEnd = new Date(Math.max(...ends) + 60000).toISOString();

          for (const s of traceSpans) {
            const svc = s.attributes?.["service.name"]?.stringValue;
            if (svc) serviceIds.add(svc);
          }
        }

        // Build logs URL with optional serviceIds for cross-workload data
        let logsUrl = `/api/logs?traceId=${traceId}&minutes=10080`;
        if (serviceIds.size > 0 && traceStart && traceEnd) {
          logsUrl += `&serviceIds=${[...serviceIds].join(",")}&startTime=${encodeURIComponent(traceStart)}&endTime=${encodeURIComponent(traceEnd)}`;
        }

        const logsRes = await fetch(logsUrl);
        if (logsRes.ok) {
          const logsData = await logsRes.json();
          setLogs(logsData.logs || []);
          setConversation(logsData.conversation || []);
        }
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [traceId]);

  const projectId = process.env.NEXT_PUBLIC_GOOGLE_CLOUD_PROJECT || "";
  const cloudTraceUrl = `https://console.cloud.google.com/traces/list?project=${projectId}&tid=${traceId}`;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </Link>
          <div>
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              Trace{" "}
              <code className="text-brand-600 text-sm font-mono bg-brand-50 px-2 py-0.5 rounded">
                {traceId.slice(0, 16)}...
              </code>
              {spans.length > 0 && (() => {
                const startMs = Math.min(...spans.map(s => new Date(s.startTime).getTime()));
                const endMs = Math.max(...spans.map(s => new Date(s.endTime).getTime()));
                const dur = endMs - startMs;
                const label = dur >= 60000 ? `${(dur / 60000).toFixed(1)}m`
                  : dur >= 1000 ? `${(dur / 1000).toFixed(1)}s`
                  : `${Math.round(dur)}ms`;
                return (
                  <span className="text-xs font-medium bg-gray-100 text-gray-700 px-2 py-0.5 rounded-full">
                    {label}
                  </span>
                );
              })()}
            </h2>
            {spans.length > 0 && (() => {
              const invId = spans.find(s =>
                s.attributes?.["gcp.vertex.agent_event_id"]?.stringValue ||
                s.attributes?.["invocation_id"]?.stringValue ||
                s.attributes?.["session_id"]?.stringValue
              );
              const id = invId?.attributes?.["gcp.vertex.agent_event_id"]?.stringValue
                || invId?.attributes?.["invocation_id"]?.stringValue
                || invId?.attributes?.["session_id"]?.stringValue;
              if (!id) return null;
              return (
                <div className="text-xs text-gray-400 font-mono mt-0.5" title={id}>
                  Invocation: {id}
                </div>
              );
            })()}
          </div>
        </div>
        <a
          href={cloudTraceUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50 text-gray-600"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          Cloud Trace
        </a>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-16 text-gray-400">
          <RefreshCw className="w-5 h-5 animate-spin mr-2" />
          Loading trace data...
        </div>
      )}

      {!loading && !error && (
        <>
          {/* Tabs */}
          <div className="flex border-b">
            <button
              onClick={() => setActiveTab("waterfall")}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === "waterfall"
                  ? "border-brand-600 text-brand-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              Waterfall ({spans.length} steps)
            </button>
            <button
              onClick={() => setActiveTab("conversation")}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-1.5 ${
                activeTab === "conversation"
                  ? "border-brand-600 text-brand-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              Prompt & Response ({conversation.length})
            </button>
            <button
              onClick={() => setActiveTab("processmap")}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-1.5 ${
                activeTab === "processmap"
                  ? "border-brand-600 text-brand-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              <GitBranch className="w-3.5 h-3.5" />
              Process Map
            </button>
            <button
              onClick={() => setActiveTab("logs")}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === "logs"
                  ? "border-brand-600 text-brand-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              Logs ({logs.length})
            </button>
          </div>

          {activeTab === "waterfall" && (
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-4">
              <TraceWaterfall
                spans={spans}
                onSpanClick={(span) => setSelectedSpan(span)}
                selectedSpanId={selectedSpan?.spanId}
              />
              {selectedSpan ? (
                <SpanDetail
                  span={selectedSpan}
                  onClose={() => setSelectedSpan(null)}
                />
              ) : (
                <div className="border rounded-lg bg-white shadow-sm p-8 text-center text-gray-400 text-sm">
                  Click a step to view details
                </div>
              )}
            </div>
          )}

          {activeTab === "conversation" && (
            <div className="max-w-3xl mx-auto space-y-3">
              {conversation.length === 0 ? (
                <div className="text-center py-12 text-gray-400 text-sm">
                  No conversation data found for this trace.
                </div>
              ) : (
                conversation.map((turn, i) => (
                  <div
                    key={i}
                    className={`flex gap-3 ${
                      turn.role === "user" ? "" : "flex-row-reverse"
                    }`}
                  >
                    <div
                      className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                        turn.role === "user"
                          ? "bg-blue-100 text-blue-600"
                          : turn.toolCall
                          ? "bg-amber-100 text-amber-600"
                          : "bg-emerald-100 text-emerald-600"
                      }`}
                    >
                      {turn.role === "user" ? (
                        <User className="w-4 h-4" />
                      ) : turn.toolCall ? (
                        <Wrench className="w-4 h-4" />
                      ) : (
                        <Bot className="w-4 h-4" />
                      )}
                    </div>
                    <div
                      className={`flex-1 max-w-[80%] rounded-lg px-4 py-3 ${
                        turn.role === "user"
                          ? "bg-blue-50 border border-blue-100"
                          : turn.toolCall
                          ? "bg-amber-50 border border-amber-100"
                          : "bg-white border shadow-sm"
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-semibold text-gray-700">
                          {turn.role === "user" ? "User" : turn.agentName}
                        </span>
                        <span className="text-[10px] text-gray-400">
                          {new Date(turn.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      {turn.toolCall ? (
                        <div className="text-sm">
                          <span className="font-mono text-amber-700 text-xs">
                            {turn.toolCall.name}
                          </span>
                          <pre className="mt-1 text-xs text-gray-600 bg-white rounded p-2 overflow-x-auto">
                            {JSON.stringify(turn.toolCall.args, null, 2)}
                          </pre>
                        </div>
                      ) : (
                        <p className="text-sm text-gray-800 whitespace-pre-wrap">
                          {turn.text}
                        </p>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === "processmap" && (
            <ProcessMap spans={spans} />
          )}

          {activeTab === "logs" && (
            <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
              <div className="max-h-[600px] overflow-y-auto">
                <table className="w-full text-xs">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr className="text-left text-gray-500 uppercase tracking-wider">
                      <th className="px-3 py-2">Time</th>
                      <th className="px-3 py-2">Severity</th>
                      <th className="px-3 py-2">Agent</th>
                      <th className="px-3 py-2">Message</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 font-mono">
                    {logs.length === 0 ? (
                      <tr>
                        <td
                          colSpan={4}
                          className="px-3 py-8 text-center text-gray-400"
                        >
                          No logs found for this trace
                        </td>
                      </tr>
                    ) : (
                      logs.map((log, i) => (
                        <tr key={i} className="hover:bg-blue-50">
                          <td className="px-3 py-1.5 text-gray-500 whitespace-nowrap">
                            {new Date(log.timestamp).toLocaleTimeString()}
                          </td>
                          <td className="px-3 py-1.5">
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                                log.severity === "ERROR"
                                  ? "bg-red-100 text-red-700"
                                  : log.severity === "WARNING"
                                  ? "bg-amber-100 text-amber-700"
                                  : "bg-gray-100 text-gray-600"
                              }`}
                            >
                              {log.severity}
                            </span>
                          </td>
                          <td className="px-3 py-1.5 text-gray-600">
                            {log.agentName}
                          </td>
                          <td className="px-3 py-1.5 text-gray-700 max-w-[600px] truncate">
                            {log.message}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
