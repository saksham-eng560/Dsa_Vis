/** Segmented switch between free-form code and LeetCode problem mode. */
import { motion } from 'framer-motion';
import { Code2, Trophy } from 'lucide-react';

import { useAppStore } from '../../stores/appStore';
import { useLeetCode, type Mode } from '../../stores/leetcodeStore';

const MODES: { id: Mode; label: string; icon: typeof Code2 }[] = [
  { id: 'free', label: 'Free code', icon: Code2 },
  { id: 'leetcode', label: 'LeetCode', icon: Trophy },
];

export function ModeToggle() {
  const mode = useLeetCode((s) => s.mode);
  const setMode = useLeetCode((s) => s.setMode);
  return (
    <div role="radiogroup" aria-label="Input mode" className="glass-inset flex gap-1 p-1">
      {MODES.map(({ id, label, icon: Icon }) => {
        const selected = mode === id;
        return (
          <button
            key={id}
            role="radio"
            aria-checked={selected}
            onClick={() => {
              if (mode === id) return;
              setMode(id);
              useAppStore.getState().clearResult();
              useAppStore.getState().setTab(id === 'leetcode' ? 'problem' : 'flowchart');
            }}
            className="focus-ring relative flex flex-1 items-center justify-center gap-2 rounded-[0.65rem] px-3 py-1.5 text-sm font-medium"
            style={{ color: selected ? 'var(--text)' : 'var(--text-muted)' }}
          >
            {selected && (
              <motion.span
                layoutId="mode-indicator"
                className="absolute inset-0 rounded-[0.65rem]"
                style={{ background: 'var(--glass-bg-active)', border: '1px solid var(--glass-border-hover)' }}
                transition={{ type: 'spring', stiffness: 380, damping: 32 }}
              />
            )}
            <span className="relative flex items-center gap-2">
              <Icon size={15} aria-hidden /> {label}
            </span>
          </button>
        );
      })}
    </div>
  );
}
