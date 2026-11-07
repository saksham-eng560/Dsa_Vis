/** Vertical stack: newest element on top, push/pop animate in and out. */
import { AnimatePresence, motion } from 'framer-motion';

import type { Highlight, Scalar } from '../../../types';
import { cellColor, matching, show } from './shared';

export function StackView({ values, highlights }: { values: Scalar[]; highlights: Highlight[] }) {
  return (
    <div className="flex flex-col items-center py-4">
      <span className="mb-2 text-xs" style={{ color: 'var(--text-faint)' }}>top</span>
      <div className="flex w-40 flex-col-reverse gap-1.5 rounded-b-2xl border-x-2 border-b-2 p-2" style={{ borderColor: 'var(--glass-border-hover)', minHeight: '3.5rem' }}>
        <AnimatePresence initial={false}>
          {values.map((value, i) => {
            const color = cellColor(matching(highlights, i));
            const isTop = i === values.length - 1;
            return (
              <motion.div
                key={`${i}-${String(value)}`}
                layout
                initial={{ opacity: 0, y: -24, scale: 0.9 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -24, scale: 0.9 }}
                transition={{ type: 'spring', stiffness: 320, damping: 26 }}
                className="flex h-10 items-center justify-center rounded-lg border font-mono text-sm font-semibold"
                style={{
                  borderColor: color ?? (isTop ? 'var(--accent-primary)' : 'var(--glass-border-hover)'),
                  background: isTop ? 'color-mix(in srgb, var(--accent-primary) 16%, transparent)' : 'var(--glass-bg-hover)',
                }}
              >
                {show(value)}
              </motion.div>
            );
          })}
        </AnimatePresence>
        {!values.length && <span className="py-2 text-center text-xs" style={{ color: 'var(--text-faint)' }}>empty</span>}
      </div>
    </div>
  );
}
