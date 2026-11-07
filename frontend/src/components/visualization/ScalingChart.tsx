/** n-vs-operations chart: reference Big-O curves with the analysed one emphasised. */
import { scaleLinear } from 'd3-scale';
import { line } from 'd3-shape';
import { motion } from 'framer-motion';
import { useMemo } from 'react';

import { growth, normalize, REFERENCE_CURVES } from '../../utils/complexity';

const W = 420;
const H = 200;
const M = { top: 12, right: 74, bottom: 28, left: 40 };
const N_MAX = 20;
const Y_MAX = 120;

const TONE_STROKE: Record<string, string> = {
  green: '#34d399', blue: '#60a5fa', yellow: '#fbbf24', orange: '#fb923c', red: '#f87171', neutral: '#a5b4fc',
};

export function ScalingChart({ notation }: { notation: string }) {
  const target = normalize(notation);
  const x = scaleLinear().domain([1, N_MAX]).range([M.left, W - M.right]);
  const y = scaleLinear().domain([0, Y_MAX]).range([H - M.bottom, M.top]).clamp(true);

  const curves = useMemo(() => {
    const names = [...new Set([...REFERENCE_CURVES, target])];
    return names.map((name) => {
      const g = growth(name);
      const pts: [number, number][] = [];
      for (let n = 1; n <= N_MAX; n += 0.25) {
        const v = g.fn(n);
        pts.push([n, Math.min(v, Y_MAX)]);
        if (v >= Y_MAX) break; // stop at the top edge instead of drawing a flat line
      }
      const path = line<[number, number]>()
        .x((d) => x(d[0]))
        .y((d) => y(d[1]))(pts);
      const last = pts[pts.length - 1] ?? [N_MAX, 0];
      return { name, path: path ?? '', tone: g.tone, labelAt: last };
    });
  }, [target, x, y]);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label={`Growth of ${target} compared with common complexities`}>
      <line x1={M.left} x2={W - M.right} y1={H - M.bottom} y2={H - M.bottom} stroke="var(--glass-border-hover)" />
      <line x1={M.left} x2={M.left} y1={M.top} y2={H - M.bottom} stroke="var(--glass-border-hover)" />
      <text x={(W - M.right + M.left) / 2} y={H - 6} textAnchor="middle" fontSize={10} fill="var(--text-faint)">input size n</text>
      <text x={12} y={H / 2} fontSize={10} fill="var(--text-faint)" transform={`rotate(-90 12 ${H / 2})`} textAnchor="middle">operations</text>
      {curves.map((c) => {
        const emphasised = c.name === target;
        return (
          <g key={c.name} opacity={emphasised ? 1 : 0.32}>
            <motion.path
              d={c.path}
              fill="none"
              stroke={TONE_STROKE[c.tone]}
              strokeWidth={emphasised ? 3.5 : 1.5}
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: emphasised ? 1.1 : 0.6 }}
              style={emphasised ? { filter: `drop-shadow(0 0 6px ${TONE_STROKE[c.tone]})` } : undefined}
            />
            <text x={x(c.labelAt[0]) + 4} y={y(c.labelAt[1])} fontSize={emphasised ? 11 : 9} fontWeight={emphasised ? 700 : 400} fill={TONE_STROKE[c.tone]} dominantBaseline="middle">
              {c.name}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
