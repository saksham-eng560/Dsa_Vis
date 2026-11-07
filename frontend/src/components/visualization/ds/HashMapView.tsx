/** Hash map as hashed buckets with chained entries (collisions visible). */
import { AnimatePresence, motion } from 'framer-motion';

import type { Highlight, Scalar } from '../../../types';
import { cellColor, matching, show } from './shared';

const BUCKETS = 8;

/** Deterministic string hash → bucket (illustrative, not Python's hash()). */
function bucketOf(key: Scalar): number {
  const s = String(key);
  let h = 0;
  for (let i = 0; i < s.length; i += 1) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return h % BUCKETS;
}

export function HashMapView({ entries, highlights }: { entries: [Scalar, Scalar][]; highlights: Highlight[] }) {
  const buckets: [Scalar, Scalar][][] = Array.from({ length: BUCKETS }, () => []);
  entries.forEach((e) => buckets[bucketOf(e[0])]?.push(e));
  return (
    <div className="grid gap-1.5 p-3" aria-label="Hash map buckets">
      {buckets.map((chain, b) => (
        <div key={b} className="flex items-center gap-2">
          <span className="w-8 shrink-0 rounded-md border py-1 text-center font-mono text-[0.65rem]" style={{ borderColor: 'var(--glass-border)', color: 'var(--text-faint)' }}>
            {b}
          </span>
          <div className="flex flex-wrap items-center gap-1.5">
            <AnimatePresence initial={false}>
              {chain.map(([k, v], i) => {
                const color = cellColor(matching(highlights, k));
                return (
                  <motion.div
                    key={String(k)}
                    layout
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    className="flex items-center gap-1"
                  >
                    {i > 0 && <span style={{ color: 'var(--text-faint)' }}>→</span>}
                    <span
                      className="rounded-lg border px-2 py-1 font-mono text-xs"
                      style={{ borderColor: color ?? 'var(--glass-border-hover)', background: color ? `color-mix(in srgb, ${color} 18%, transparent)` : 'var(--glass-bg-hover)' }}
                    >
                      <b>{show(k)}</b>
                      <span style={{ color: 'var(--text-faint)' }}> : </span>
                      {show(v)}
                    </span>
                  </motion.div>
                );
              })}
            </AnimatePresence>
            {!chain.length && <span className="text-xs" style={{ color: 'var(--text-faint)' }}>∅</span>}
          </div>
        </div>
      ))}
    </div>
  );
}
