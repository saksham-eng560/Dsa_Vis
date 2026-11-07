/** 2-D grid (DP tables, boards) with cell highlights. */
import { motion } from 'framer-motion';

import type { Highlight, Scalar } from '../../../types';
import { cellColor, matching, show } from './shared';

export function MatrixView({ rows, highlights }: { rows: Scalar[][]; highlights: Highlight[] }) {
  const cols = Math.max(0, ...rows.map((r) => r.length));
  return (
    <div className="overflow-auto p-3 scroll-thin">
      <table className="mx-auto border-separate border-spacing-1 font-mono text-xs" aria-label="Matrix">
        <thead>
          <tr>
            <th />
            {Array.from({ length: cols }, (_, c) => (
              <th key={c} className="px-1 font-normal" style={{ color: 'var(--text-faint)' }}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, r) => (
            <tr key={r}>
              <th className="pr-1 font-normal" style={{ color: 'var(--text-faint)' }}>{r}</th>
              {row.map((value, c) => {
                const hs = matching(highlights, [r, c]);
                const color = cellColor(hs);
                return (
                  <motion.td
                    key={c}
                    title={hs.map((h) => h.label).join(', ') || undefined}
                    animate={{ backgroundColor: color ? `color-mix(in srgb, ${color} 30%, transparent)` : 'var(--glass-bg)', scale: color ? 1.06 : 1 }}
                    className="h-9 min-w-9 rounded-md border px-1.5 text-center font-semibold"
                    style={{ borderColor: color ?? 'var(--glass-border)' }}
                  >
                    {show(value)}
                  </motion.td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
