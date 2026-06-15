"use client";

import { useState } from "react";

export interface LineSeries {
  name: string;
  color: string;
  points: { x: string; y: number }[]; // x is date label
}

interface Props {
  series: LineSeries[];
  height?: number;
  yLabel?: string;
  yFormatter?: (v: number) => string;
}

/** Lightweight multi-line chart (inline SVG, no external deps). */
export default function LineChart({ series, height = 260, yLabel, yFormatter }: Props) {
  const [hover, setHover] = useState<{ xIdx: number; left: number; top: number } | null>(null);

  const allXs = Array.from(new Set(series.flatMap((s) => s.points.map((p) => p.x)))).sort();
  const maxY = Math.max(1, ...series.flatMap((s) => s.points.map((p) => p.y)));
  const padding = { top: 16, right: 16, bottom: 36, left: 56 };
  const width = 900;
  const innerW = width - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;

  function xPos(idx: number): number {
    if (allXs.length <= 1) return padding.left + innerW / 2;
    return padding.left + (idx / (allXs.length - 1)) * innerW;
  }
  function yPos(v: number): number {
    return padding.top + innerH - (v / maxY) * innerH;
  }

  const fmt = yFormatter || ((v: number) => String(v));

  // Y-axis ticks
  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((t) => t * maxY);

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="xMidYMid meet"
        className="w-full h-auto"
        onMouseLeave={() => setHover(null)}
      >
        {/* Grid lines */}
        {yTicks.map((t, i) => {
          const y = yPos(t);
          return (
            <g key={i}>
              <line x1={padding.left} x2={width - padding.right} y1={y} y2={y} stroke="#e5e7eb" strokeDasharray="3,3" />
              <text x={padding.left - 6} y={y + 4} textAnchor="end" fontSize="10" fill="#6b7280">
                {fmt(t)}
              </text>
            </g>
          );
        })}

        {/* X-axis labels */}
        {allXs.map((x, i) => (
          <text
            key={x}
            x={xPos(i)}
            y={height - padding.bottom + 16}
            textAnchor="middle"
            fontSize="10"
            fill="#6b7280"
          >
            {x}
          </text>
        ))}

        {/* Y-axis label */}
        {yLabel && (
          <text
            x={padding.left - 44}
            y={padding.top + innerH / 2}
            transform={`rotate(-90 ${padding.left - 44} ${padding.top + innerH / 2})`}
            textAnchor="middle"
            fontSize="10"
            fill="#6b7280"
          >
            {yLabel}
          </text>
        )}

        {/* Lines */}
        {series.map((s) => {
          const pts = s.points
            .map((p) => {
              const idx = allXs.indexOf(p.x);
              if (idx < 0) return null;
              return `${xPos(idx)},${yPos(p.y)}`;
            })
            .filter(Boolean);
          if (pts.length === 0) return null;
          return (
            <g key={s.name}>
              <polyline
                points={pts.join(" ")}
                fill="none"
                stroke={s.color}
                strokeWidth={2}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              {s.points.map((p) => {
                const idx = allXs.indexOf(p.x);
                if (idx < 0) return null;
                return (
                  <circle
                    key={p.x}
                    cx={xPos(idx)}
                    cy={yPos(p.y)}
                    r={3}
                    fill={s.color}
                    stroke="#fff"
                    strokeWidth={1.5}
                  />
                );
              })}
            </g>
          );
        })}

        {/* Hover tracker */}
        {allXs.map((x, i) => (
          <rect
            key={`h-${x}`}
            x={xPos(i) - (innerW / Math.max(allXs.length, 1)) / 2}
            y={padding.top}
            width={innerW / Math.max(allXs.length, 1)}
            height={innerH}
            fill="transparent"
            onMouseEnter={(e) => {
              const rect = (e.currentTarget.ownerSVGElement as SVGSVGElement).getBoundingClientRect();
              setHover({
                xIdx: i,
                left: ((xPos(i) / width) * rect.width),
                top: padding.top,
              });
            }}
          />
        ))}
      </svg>

      {hover && (
        <div
          className="absolute pointer-events-none bg-white border rounded-md shadow-lg px-2.5 py-1.5 text-xs min-w-[140px]"
          style={{ left: hover.left + 8, top: hover.top }}
        >
          <div className="font-semibold text-gray-700 mb-1">{allXs[hover.xIdx]}</div>
          {series.map((s) => {
            const pt = s.points.find((p) => p.x === allXs[hover.xIdx]);
            if (!pt) return null;
            return (
              <div key={s.name} className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-sm" style={{ backgroundColor: s.color }} />
                <span className="text-gray-600">{s.name}:</span>
                <span className="font-semibold text-gray-800 ml-auto">{fmt(pt.y)}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
