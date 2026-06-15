"use client";

import { useState } from "react";

export interface BarGroup {
  label: string;
  values: { name: string; value: number; color: string }[];
}

interface Props {
  groups: BarGroup[];
  height?: number;
  yLabel?: string;
  yFormatter?: (v: number) => string;
}

/** Grouped bar chart (inline SVG). */
export default function GroupedBarChart({ groups, height = 280, yLabel, yFormatter }: Props) {
  const [hover, setHover] = useState<{ gIdx: number; vIdx: number; left: number; top: number } | null>(null);

  if (groups.length === 0) {
    return <div className="text-center py-12 text-gray-400 text-sm">No data</div>;
  }

  const maxY = Math.max(1, ...groups.flatMap((g) => g.values.map((v) => v.value)));
  const padding = { top: 16, right: 16, bottom: 36, left: 64 };
  const width = 900;
  const innerW = width - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;

  const groupWidth = innerW / groups.length;
  const valueCount = Math.max(1, ...groups.map((g) => g.values.length));
  const barW = Math.max(4, (groupWidth * 0.8) / valueCount);
  const groupGap = groupWidth * 0.1;

  const fmt = yFormatter || ((v: number) => String(v));
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
          const y = padding.top + innerH - (t / maxY) * innerH;
          return (
            <g key={i}>
              <line x1={padding.left} x2={width - padding.right} y1={y} y2={y} stroke="#e5e7eb" strokeDasharray="3,3" />
              <text x={padding.left - 6} y={y + 4} textAnchor="end" fontSize="10" fill="#6b7280">
                {fmt(t)}
              </text>
            </g>
          );
        })}

        {yLabel && (
          <text
            x={padding.left - 52}
            y={padding.top + innerH / 2}
            transform={`rotate(-90 ${padding.left - 52} ${padding.top + innerH / 2})`}
            textAnchor="middle"
            fontSize="10"
            fill="#6b7280"
          >
            {yLabel}
          </text>
        )}

        {/* Bars */}
        {groups.map((g, gi) => {
          const gStartX = padding.left + gi * groupWidth + groupGap;
          return (
            <g key={g.label}>
              {g.values.map((v, vi) => {
                const x = gStartX + vi * barW;
                const barH = (v.value / maxY) * innerH;
                const y = padding.top + innerH - barH;
                return (
                  <rect
                    key={v.name}
                    x={x}
                    y={y}
                    width={barW - 2}
                    height={barH}
                    fill={v.color}
                    rx={2}
                    onMouseEnter={(e) => {
                      const rect = (e.currentTarget.ownerSVGElement as SVGSVGElement).getBoundingClientRect();
                      setHover({
                        gIdx: gi,
                        vIdx: vi,
                        left: (x / width) * rect.width,
                        top: (y / height) * rect.height,
                      });
                    }}
                  />
                );
              })}
              <text
                x={gStartX + (groupWidth - 2 * groupGap) / 2}
                y={height - padding.bottom + 16}
                textAnchor="middle"
                fontSize="10"
                fill="#6b7280"
              >
                {g.label}
              </text>
            </g>
          );
        })}
      </svg>

      {hover && (() => {
        const v = groups[hover.gIdx].values[hover.vIdx];
        return (
          <div
            className="absolute pointer-events-none bg-white border rounded-md shadow-lg px-2.5 py-1.5 text-xs"
            style={{ left: hover.left, top: hover.top - 40 }}
          >
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-sm" style={{ backgroundColor: v.color }} />
              <span className="font-semibold text-gray-800">{v.name}</span>
            </div>
            <div className="text-gray-600 mt-0.5">
              {groups[hover.gIdx].label}: <b>{fmt(v.value)}</b>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
