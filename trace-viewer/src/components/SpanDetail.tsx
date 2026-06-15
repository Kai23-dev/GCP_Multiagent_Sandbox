"use client";

import { X, Clock, Hash, AlertCircle, Tag } from "lucide-react";

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

interface Props {
  span: Span;
  onClose: () => void;
}

export default function SpanDetail({ span, onClose }: Props) {
  const startMs = new Date(span.startTime).getTime();
  const endMs = new Date(span.endTime).getTime();
  const duration = endMs - startMs;
  const isError = span.status?.code === 2;

  const attrs = span.attributes || {};
  const importantAttrs = [
    "agent.name",
    "agent.resource",
    "agent.query_length",
    "agent.response_length",
    "agent.http_status",
    "agent.error",
    "agent.attempt",
    "agent.user_id",
  ];

  return (
    <div className="border rounded-lg bg-white shadow-lg overflow-hidden">
      {/* Header */}
      <div
        className={`px-4 py-3 flex items-center justify-between ${
          isError ? "bg-red-50 border-b border-red-200" : "bg-gray-50 border-b"
        }`}
      >
        <div className="flex items-center gap-2 min-w-0">
          <div
            className={`w-3 h-3 rounded-full flex-shrink-0 ${
              isError ? "bg-red-500" : "bg-blue-500"
            }`}
          />
          <div className="min-w-0">
            {span.agentName && (
              <div className="text-xs text-brand-600 font-medium">{span.agentName}</div>
            )}
            <h3 className="font-semibold text-gray-900 text-sm truncate">{span.name}</h3>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-200 rounded transition-colors"
        >
          <X className="w-4 h-4 text-gray-500" />
        </button>
      </div>

      <div className="p-4 space-y-4">
        {/* Timing */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-gray-50 rounded p-3">
            <div className="text-[10px] text-gray-500 uppercase tracking-wider flex items-center gap-1">
              <Clock className="w-3 h-3" /> Duration
            </div>
            <div className="text-lg font-bold text-gray-900 mt-0.5">
              {duration >= 1000
                ? `${(duration / 1000).toFixed(2)}s`
                : `${duration}ms`}
            </div>
          </div>
          <div className="bg-gray-50 rounded p-3">
            <div className="text-[10px] text-gray-500 uppercase tracking-wider">
              Start
            </div>
            <div className="text-xs font-mono text-gray-700 mt-1">
              {new Date(span.startTime).toLocaleTimeString()}
            </div>
          </div>
          <div className="bg-gray-50 rounded p-3">
            <div className="text-[10px] text-gray-500 uppercase tracking-wider">
              End
            </div>
            <div className="text-xs font-mono text-gray-700 mt-1">
              {new Date(span.endTime).toLocaleTimeString()}
            </div>
          </div>
        </div>

        {/* IDs */}
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 text-xs">
            <Hash className="w-3 h-3 text-gray-400" />
            <span className="text-gray-500 w-24">Span ID</span>
            <code className="text-gray-700 bg-gray-100 px-1.5 py-0.5 rounded font-mono text-[11px]">
              {span.spanId}
            </code>
          </div>
          {span.parentSpanId && (
            <div className="flex items-center gap-2 text-xs">
              <Hash className="w-3 h-3 text-gray-400" />
              <span className="text-gray-500 w-24">Parent Span</span>
              <code className="text-gray-700 bg-gray-100 px-1.5 py-0.5 rounded font-mono text-[11px]">
                {span.parentSpanId}
              </code>
            </div>
          )}
        </div>

        {/* Error */}
        {isError && span.status?.message && (
          <div className="bg-red-50 border border-red-200 rounded p-3">
            <div className="flex items-center gap-1.5 text-red-700 text-xs font-medium mb-1">
              <AlertCircle className="w-3.5 h-3.5" />
              Error
            </div>
            <pre className="text-xs text-red-600 whitespace-pre-wrap font-mono">
              {span.status.message}
            </pre>
          </div>
        )}

        {/* Attributes */}
        {Object.keys(attrs).length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-1">
              <Tag className="w-3 h-3" /> Attributes
            </h4>
            <div className="bg-gray-50 rounded divide-y divide-gray-200">
              {importantAttrs
                .filter((key) => attrs[key])
                .map((key) => (
                  <div key={key} className="flex px-3 py-1.5 text-xs">
                    <span className="text-gray-500 w-40 flex-shrink-0 font-mono">
                      {key}
                    </span>
                    <span className="text-gray-800 font-mono break-all">
                      {attrs[key]?.stringValue || attrs[key]?.intValue || "—"}
                    </span>
                  </div>
                ))}
              {Object.entries(attrs)
                .filter(([key]) => !importantAttrs.includes(key))
                .map(([key, val]) => (
                  <div key={key} className="flex px-3 py-1.5 text-xs">
                    <span className="text-gray-400 w-40 flex-shrink-0 font-mono">
                      {key}
                    </span>
                    <span className="text-gray-600 font-mono break-all">
                      {val?.stringValue || val?.intValue || "—"}
                    </span>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
