/**
 * Hero motion graphic: a miniature CodeLens window replaying a real bubble
 * sort — the highlighted code line and the animated bars stay in sync.
 */
import { motion } from 'framer-motion';
import { useEffect, useMemo, useState } from 'react';

import { bubbleFrames, DEMO_CODE } from './sortingDemo';

const INPUT = [7, 3, 9, 2, 6, 4, 8, 1];
// Each bar keeps a stable identity (its original value) so layout animations glide.
const SPRING = { type: 'spring', stiffness: 380, damping: 30 } as const;

export function LiveDemo() {
  const frames = useMemo(() => bubbleFrames(INPUT), []);
  const [k, setK] = useState(0);
  useEffect(() => {
    const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduced) {
      setK(frames.length - 1);
      return;
    }
    const t = window.setInterval(() => setK((x) => (x + 1) % (frames.length + 6)), 420);
    return () => window.clearInterval(t);
  }, [frames.length]);
  const f = frames[Math.min(k, frames.length - 1)]!;
  const max = Math.max(...INPUT);

  return (
    <div className="overflow-hidden rounded-[28px] border shadow-2xl" style={{ background: 'var(--surface-1)', borderColor: 'var(--separator)', boxShadow: 'var(--glass-shadow-glow)' }}>
      <div className="flex items-center gap-2 border-b px-4 py-3" style={{ borderColor: 'var(--separator)' }}>
        {['#ff5f57', '#febc2e', '#28c840'].map((c) => <span key={c} className="h-3 w-3 rounded-full" style={{ background: c }} />)}
        <span className="ml-3 text-xs font-medium" style={{ color: 'var(--text-faint)' }}>bubble_sort.py — Dry Run</span>
        <span className="ml-auto font-mono text-xs" style={{ color: 'var(--text-faint)' }}>step {Math.min(k, frames.length - 1) + 1} / {frames.length}</span>
      </div>
      <div className="grid gap-0 md:grid-cols-[1.05fr_1fr]">
        <pre className="m-0 overflow-hidden px-5 py-5 font-mono text-[12.5px] leading-[1.9]" aria-hidden>
          {DEMO_CODE.map((line, i) => {
            const active = f.line === i + 1;
            return (
              <div key={i} className="relative flex">
                {active && (
                  <motion.span
                    layoutId="demo-line"
                    className="absolute -inset-x-2 inset-y-0 rounded-md"
                    style={{ background: 'color-mix(in srgb, var(--accent-primary) 20%, transparent)' }}
                    transition={SPRING}
                  />
                )}
                <span className="relative mr-4 w-4 select-none text-right" style={{ color: 'var(--text-faint)' }}>{i + 1}</span>
                <span className="relative" style={{ color: active ? 'var(--text)' : 'var(--text-muted)' }}>{line}</span>
              </div>
            );
          })}
        </pre>
        <div className="flex h-60 items-end justify-center gap-2.5 border-t px-6 pb-6 pt-8 md:h-auto md:border-l md:border-t-0" style={{ borderColor: 'var(--separator)' }}>
          {f.values.map((v, idx) => {
            const comparing = f.compare?.includes(idx);
            const done = idx >= f.sortedFrom;
            const color = comparing ? (f.swapped ? 'var(--accent-orange)' : 'var(--accent-primary)') : done ? 'var(--accent-secondary)' : 'var(--surface-3)';
            return (
              <motion.div key={v} layout transition={SPRING} className="flex w-8 flex-col items-center gap-2">
                <motion.div
                  className="w-full rounded-lg"
                  animate={{ height: `${(v / max) * 150 + 18}px`, backgroundColor: color, scale: comparing ? 1.06 : 1 }}
                  transition={{ duration: 0.25 }}
                />
                <span className="font-mono text-xs" style={{ color: comparing ? 'var(--text)' : 'var(--text-faint)' }}>{v}</span>
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
