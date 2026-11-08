/** Helpers shared by the data-structure renderers. */
import { motion } from 'framer-motion';

import { HIGHLIGHT_COLORS } from '../../../styles/theme';
import type { Highlight, HighlightTarget, Scalar } from '../../../types';

/** Highlights whose target matches `target` (loose: 3 == "3"). */
export function matching(highlights: Highlight[], target: HighlightTarget): Highlight[] {
  const key = JSON.stringify(target);
  return highlights.filter((h) => JSON.stringify(h.target) === key || String(h.target) === String(target));
}

/** Display string for a cell value. */
export function show(value: Scalar): string {
  if (value === null) return 'None';
  if (typeof value === 'boolean') return value ? 'True' : 'False';
  if (typeof value === 'string') return value.length > 14 ? `${value.slice(0, 13)}…` : value;
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

/** First highlight colour (changed/red wins so swaps stand out). */
export function cellColor(hs: Highlight[]): string | undefined {
  const pick = hs.find((h) => h.color === 'red') ?? hs[0];
  return pick ? HIGHLIGHT_COLORS[pick.color] : undefined;
}

/** Pointer labels rendered under a cell. */
export function PointerLabels({ highlights }: { highlights: Highlight[] }) {
  const labels = highlights.filter((h) => h.label && h.label !== 'changed' && h.label !== 'updated');
  return (
    <div className="flex min-h-[1.25rem] flex-col items-center gap-0.5">
      {labels.map((h) => (
        <motion.span
          key={h.label}
          layoutId={`ptr-${h.label}`}
          className="font-mono text-[0.68rem] font-semibold leading-none"
          style={{ color: HIGHLIGHT_COLORS[h.color] }}
          transition={{ type: 'spring', stiffness: 300, damping: 28 }}
        >
          ▲ {h.label}
        </motion.span>
      ))}
    </div>
  );
}

export function EmptyState({ text }: { text: string }) {
  return (
    <p className="py-10 text-center text-sm" style={{ color: 'var(--text-faint)' }}>
      {text}
    </p>
  );
}
