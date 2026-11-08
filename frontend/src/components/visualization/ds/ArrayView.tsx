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
  if (!values.length) return <p className="py-6 text-center font-mono text-sm" style={{ color: 'var(--text-faint)' }}>[ ] empty</p>;
  return (
    <LayoutGroup>
      <div className="flex items-end justify-center gap-1.5 overflow-x-auto px-2 py-4 scroll-thin" role="list" aria-label="Array contents">
        {edgeLabels && <span className="self-center pr-2 text-xs" style={{ color: 'var(--text-faint)' }}>{edgeLabels[0]} →</span>}
        {values.map((value, i) => {
          const hs = matching(highlights, i);
          const color = cellColor(hs);
          return (
            <div key={i} className="flex flex-col items-center gap-1" role="listitem">
              <span className="font-mono text-[0.65rem]" style={{ color: 'var(--text-faint)' }}>{i}</span>
              <motion.div
                layout
                animate={{ scale: color ? 1.08 : 1, y: color ? -4 : 0, backgroundColor: color ?? 'var(--surface-3)', color: color ? '#ffffff' : 'var(--text)' }}
                transition={{ type: 'spring', stiffness: 320, damping: 24 }}
                className="flex h-12 min-w-12 items-center justify-center rounded-[12px] px-2 text-[15px] font-semibold tabular-nums"
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
