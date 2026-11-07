/** Variable watch table; values that just changed flash. */
import { AnimatePresence, motion } from 'framer-motion';

import type { DryRunStep } from '../../types';

export function VariableWatch({ step }: { step: DryRunStep | undefined }) {
  const entries = Object.entries(step?.variables ?? {});
  return (
    <div className="glass-inset flex min-h-0 flex-col p-3">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-faint)' }}>
        Variables {step && <span className="normal-case tracking-normal">· {step.function === '<module>' ? 'global scope' : `${step.function}()`}</span>}
      </h3>
      {entries.length === 0 ? (
        <p className="text-xs" style={{ color: 'var(--text-faint)' }}>No variables in scope yet.</p>
      ) : (
        <dl className="grid max-h-56 grid-cols-[auto_1fr] gap-x-3 gap-y-1 overflow-auto font-mono text-xs scroll-thin">
          <AnimatePresence initial={false}>
            {entries.map(([name, value]) => {
              const changed = step?.changed.includes(name);
              return (
                <motion.div key={name} className="contents" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <dt className="font-semibold" style={{ color: changed ? 'var(--accent-warning)' : 'var(--accent-primary)' }}>{name}</dt>
                  <motion.dd
                    key={value}
                    initial={changed ? { backgroundColor: 'rgba(251,191,36,0.35)' } : false}
                    animate={{ backgroundColor: 'rgba(251,191,36,0)' }}
                    transition={{ duration: 0.9 }}
                    className="truncate rounded px-1"
                    title={value}
                  >
                    {value}
                  </motion.dd>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </dl>
      )}
    </div>
  );
}
