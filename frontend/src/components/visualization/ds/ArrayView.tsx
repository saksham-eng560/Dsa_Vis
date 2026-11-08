/** Horizontal boxes with index labels, pointer arrows and swap highlighting. */
import { LayoutGroup, motion } from 'framer-motion';

import type { Highlight, Scalar } from '../../../types';
import { cellColor, matching, PointerLabels, show } from './shared';

interface ArrayViewProps {
  values: Scalar[];
  highlights: Highlight[];
  /** Optional caption per orientation (e.g. "front"/"rear" for queues). */
  edgeLabels?: [string, string];
}

export function ArrayView({ values, highlights, edgeLabels }: ArrayViewProps) {
  // cells shrink (48px → 24px) as the array grows, so it fits the card instead of scrolling
  const cell = Math.max(24, Math.min(48, Math.floor(560 / Math.max(values.length, 1)) - 6));
  if (!values.length) return <p className="py-6 text-center font-mono text-sm" style={{ color: 'var(--text-faint)' }}>[ ] empty</p>;
  return (
    <LayoutGroup>
      <div className="flex items-end justify-center gap-1.5 overflow-x-auto px-1 py-4 scroll-thin" role="list" aria-label="Array contents">
        {edgeLabels && <span className="self-center pr-2 text-xs" style={{ color: 'var(--text-faint)' }}>{edgeLabels[0]} →</span>}
        {values.map((value, i) => {
          const hs = matching(highlights, i);
          const color = cellColor(hs);
          return (
            <div key={i} className="flex min-w-0 flex-col items-center gap-1" style={{ flex: `0 1 ${cell}px`, minWidth: 22 }} role="listitem">
              <span className="font-mono text-[0.65rem]" style={{ color: 'var(--text-faint)' }}>{i}</span>
              <motion.div
                layout
                animate={{ scale: color ? 1.08 : 1, y: color ? -4 : 0, backgroundColor: color ?? 'var(--surface-3)', color: color ? '#ffffff' : 'var(--text)' }}
                transition={{ type: 'spring', stiffness: 320, damping: 24 }}
                className="flex w-full items-center justify-center rounded-[10px] font-semibold tabular-nums"
                style={{ height: cell, fontSize: cell >= 40 ? 15 : cell >= 30 ? 13 : 11 }}
              >
                <motion.span key={String(value)} initial={{ y: -8, opacity: 0 }} animate={{ y: 0, opacity: 1 }}>
                  {show(value)}
                </motion.span>
              </motion.div>
              <PointerLabels highlights={hs} />
            </div>
          );
        })}
        {edgeLabels && <span className="self-center pl-2 text-xs" style={{ color: 'var(--text-faint)' }}>← {edgeLabels[1]}</span>}
      </div>
    </LayoutGroup>
  );
}
